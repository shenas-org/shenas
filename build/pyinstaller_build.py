"""Build standalone binaries for shenas using PyInstaller.

Usage:
    uv run python build/pyinstaller_build.py                  # build all (onedir)
    uv run python build/pyinstaller_build.py shenas            # build one
    uv run python build/pyinstaller_build.py --desktop          # onefile into Tauri binaries/
    uv run python build/pyinstaller_build.py --list            # list targets
"""

from __future__ import annotations

import argparse
import importlib.metadata
import platform
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist" / "pyinstaller"
DESKTOP_BIN_DIR = ROOT / "app" / "desktop" / "src-tauri" / "binaries"
WORK_DIR = ROOT / "build" / "_pyinstaller_work"

# All shenas namespace packages that are discovered via entry_points().
# PyInstaller can't trace these dynamically, so we include them as
# hidden imports.
_HIDDEN_IMPORTS = [
    # Our packages
    "app",
    "app.server",
    "app.server_cli",
    "app.api",
    "app.api.db",
    "app.api.plugins",
    "app.api.sync",
    "app.api.transforms",
    "app.cli",
    "app.cli.main",
    "app.cli.client",
    "app.cli.commands",
    "app.cli.commands.pipe",
    "app.cli.commands.component",
    "app.cli.commands.config_cmd",
    "app.cli.commands.db_cmd",
    "app.cli.commands.schema_cmd",
    "app.cli.commands.service",
    "app.cli.commands.theme_cmd",
    "app.cli.commands.transform_cmd",
    "app.cli.commands.ui_cmd",
    "app.db",
    "app.transforms",
    "app.telemetry",
    "app.telemetry.setup",
    "app.telemetry.exporters",
    "app.telemetry.dispatcher",
    "app.telemetry.schema",
    "scheduler",
    "scheduler.cli",
    "scheduler.daemon",
    "repository",
    # Plugin namespace packages (discovered via entry_points)
    "shenas_pipes",
    "shenas_pipes.core",
    "shenas_pipes.garmin",
    "shenas_pipes.lunchmoney",
    "shenas_pipes.obsidian",
    "shenas_pipes.gmail",
    "shenas_pipes.gcalendar",
    "shenas_pipes.gtakeout",
    "shenas_pipes.duolingo",
    "shenas_pipes.spotify",
    "shenas_schemas",
    "shenas_schemas.core",
    "shenas_schemas.fitness",
    "shenas_schemas.finance",
    "shenas_schemas.outcomes",
    "shenas_schemas.habits",
    "shenas_components",
    "shenas_components.fitness_dashboard",
    "shenas_components.data_table",
    "shenas_themes",
    "shenas_themes.default",
    "shenas_themes.dark",
    "shenas_ui",
    "shenas_ui.default",
    # Key dependencies with dynamic imports
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "multipart",
    "opentelemetry.instrumentation.fastapi",
    "opentelemetry.instrumentation.httpx",
]


def _target_triple() -> str:
    """Return the Rust-style target triple for the current platform."""
    machine = platform.machine().lower()
    arch_map = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}
    arch = arch_map.get(machine, machine)

    system = platform.system().lower()
    if system == "linux":
        return f"{arch}-unknown-linux-gnu"
    if system == "darwin":
        return f"{arch}-apple-darwin"
    if system == "windows":
        return f"{arch}-pc-windows-msvc"
    return f"{arch}-{system}"


def _collect_dist_info_datas() -> list[tuple[str, str]]:
    """Collect .dist-info directories so importlib.metadata.entry_points() works at runtime."""
    datas: list[tuple[str, str]] = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata["Name"] or ""
        if name.startswith("shenas-") or name in ("dlt", "duckdb"):
            if dist._path and dist._path.exists():  # noqa: SLF001
                datas.append((str(dist._path), dist._path.name))
    return datas


def _collect_package_datas() -> list[str]:
    """Packages whose non-.py data files (JSON, CSS, HTML, static) must be included.

    Note: we intentionally exclude 'app' and 'dlt' from --collect-data because
    they pull in huge amounts of unwanted data (node_modules, desktop build
    artifacts, dlt internal fixtures). Instead we use --add-data for specific
    files from those packages.
    """
    return [
        "shenas_pipes",
        "shenas_schemas",
        "shenas_components",
        "shenas_themes",
        "shenas_ui",
    ]


def _collect_explicit_datas() -> list[tuple[str, str]]:
    """Specific data files from app/ and dlt that are needed at runtime."""
    datas: list[tuple[str, str]] = []
    # app/static/ contains the fallback HTML
    static_dir = ROOT / "app" / "static"
    if static_dir.is_dir():
        datas.append((str(static_dir), "app/static"))
    return datas


# ---- ELF execstack patching ----

_PT_GNU_STACK = 0x6474E551
_PF_X = 0x1


def _patch_elf_execstack(path: Path) -> bool:
    """Clear PF_X from GNU_STACK in a 64-bit ELF file. Returns True if patched."""
    try:
        with open(path, "r+b") as f:
            ident = f.read(16)
            if ident[:4] != b"\x7fELF" or ident[4] != 2:
                return False

            f.seek(32)
            phoff = struct.unpack("<Q", f.read(8))[0]
            f.seek(54)
            phentsize = struct.unpack("<H", f.read(2))[0]
            phnum = struct.unpack("<H", f.read(2))[0]

            for i in range(phnum):
                off = phoff + i * phentsize
                f.seek(off)
                p_type = struct.unpack("<I", f.read(4))[0]
                if p_type == _PT_GNU_STACK:
                    f.seek(off + 4)
                    p_flags = struct.unpack("<I", f.read(4))[0]
                    if p_flags & _PF_X:
                        f.seek(off + 4)
                        f.write(struct.pack("<I", p_flags & ~_PF_X))
                        return True
                    break
    except Exception:
        pass
    return False


def _find_libpython() -> Path | None:
    """Locate libpython shared library by inspecting the Python binary's dependencies."""
    python_bin = Path(sys.executable).resolve()

    # Method 1: use ldd to find linked libpython
    try:
        result = subprocess.run(["ldd", str(python_bin)], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if "libpython" in line and "=>" in line:
                # Format: "libpython3.11.so.1.0 => /path/to/lib (0x...)"
                parts = line.strip().split("=>")
                if len(parts) == 2:
                    path = parts[1].strip().split("(")[0].strip()
                    if path and Path(path).exists():
                        return Path(path)
    except Exception:
        pass

    # Method 2: search near the Python binary
    python_home = python_bin.parent.parent / "lib"
    for candidate in python_home.glob("libpython*.so*"):
        if candidate.is_file() and not candidate.is_symlink():
            return candidate

    return None


def _patch_source_libpython() -> Path | None:
    """Create a patched copy of libpython with executable stack flag cleared.

    Returns the path to the patched copy, or None if patching wasn't needed.
    For --onefile mode, we pass this to PyInstaller via --add-binary to
    override the bundled libpython.
    """
    if platform.system() != "Linux":
        return None

    libpython = _find_libpython()
    if libpython is None:
        print("  WARNING: Could not locate libpython shared library")
        return None

    # Check if it actually needs patching
    try:
        with open(libpython, "rb") as f:
            ident = f.read(16)
            if ident[:4] != b"\x7fELF" or ident[4] != 2:
                return None
            f.seek(32)
            phoff = struct.unpack("<Q", f.read(8))[0]
            f.seek(54)
            phentsize = struct.unpack("<H", f.read(2))[0]
            phnum = struct.unpack("<H", f.read(2))[0]
            needs_patch = False
            for i in range(phnum):
                off = phoff + i * phentsize
                f.seek(off)
                p_type = struct.unpack("<I", f.read(4))[0]
                if p_type == _PT_GNU_STACK:
                    f.seek(off + 4)
                    p_flags = struct.unpack("<I", f.read(4))[0]
                    needs_patch = bool(p_flags & _PF_X)
                    break
            if not needs_patch:
                print(f"  {libpython.name}: no executable stack flag, skipping patch")
                return None
    except Exception:
        return None

    # Create a patched copy
    patched = WORK_DIR / libpython.name
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(libpython, patched)
    if _patch_elf_execstack(patched):
        print(f"  Created patched copy of {libpython.name} at {patched}")
        return patched
    return None


def _patch_execstack_dir(directory: Path) -> None:
    """Patch all .so files in a directory (for --onedir post-build)."""
    for so_file in directory.glob("*.so*"):
        if _patch_elf_execstack(so_file):
            print(f"  Patched {so_file.name}: cleared executable stack flag")


# ---- Build targets ----

TARGETS = {
    "shenas": {
        "entry": BUILD_DIR / "shenas_entry.py",
        "description": "Shenas server",
    },
    "shenasctl": {
        "entry": BUILD_DIR / "shenasctl_entry.py",
        "description": "Shenas CLI",
    },
    "shenas-scheduler": {
        "entry": BUILD_DIR / "shenas_scheduler_entry.py",
        "description": "Shenas sync scheduler",
    },
}


def build_target(
    name: str,
    target: dict[str, Path | str],
    *,
    onefile: bool,
    dist_dir: Path,
    patched_libpython: Path | None = None,
) -> Path:
    """Build a single PyInstaller target. Returns the output path."""
    triple = _target_triple()
    output_name = f"{name}-{triple}"

    print(f"\n{'=' * 60}")
    print(f"Building {name} ({target['description']}) [{'onefile' if onefile else 'onedir'}]")
    print(f"{'=' * 60}\n")

    sep = _sep()
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile" if onefile else "--onedir",
        f"--name={output_name}",
        f"--distpath={dist_dir}",
        f"--workpath={WORK_DIR / name}",
        f"--specpath={WORK_DIR}",
        # Hidden imports for dynamic loading
        *[f"--hidden-import={mod}" for mod in _HIDDEN_IMPORTS],
        # Package data (transforms.json, static files, CSS, HTML)
        *[f"--collect-data={pkg}" for pkg in _collect_package_datas()],
        # Explicit data files from packages too large for --collect-data
        *[f"--add-data={src}{sep}{dest}" for src, dest in _collect_explicit_datas()],
        # .dist-info directories for importlib.metadata
        *[f"--add-data={src}{sep}{dest}" for src, dest in _collect_dist_info_datas()],
        # Override bundled libpython with patched copy (execstack fix)
        *([f"--add-binary={patched_libpython}{sep}."] if patched_libpython else []),
        # Exclude heavyweight modules not needed at runtime
        "--exclude-module=pytest",
        "--exclude-module=_pytest",
        "--exclude-module=py",
        "--exclude-module=setuptools",
        "--exclude-module=pip",
        "--exclude-module=wheel",
        "--exclude-module=distutils",
        # Search path: repo root so `app`, `scheduler`, `repository` resolve
        f"--paths={ROOT}",
        # Clean build
        "--clean",
        "--noconfirm",
        str(target["entry"]),
    ]

    print(f"Running PyInstaller with {len(cmd)} args...")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\nFailed to build {name} (exit code {result.returncode})")
        sys.exit(result.returncode)

    if onefile:
        output_path = dist_dir / output_name
        if platform.system() == "Windows":
            output_path = output_path.with_suffix(".exe")
    else:
        output_path = dist_dir / output_name / output_name
        if platform.system() == "Windows":
            output_path = output_path.with_suffix(".exe")

    print(f"\nBuilt: {output_path}")
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"Size: {size_mb:.1f} MB")
        if not onefile:
            dir_path = output_path.parent
            total = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
            print(f"Total directory: {total / (1024 * 1024):.1f} MB")
            # Post-build patch for --onedir
            if platform.system() == "Linux":
                _patch_execstack_dir(output_path.parent / "_internal")

    return output_path


def _sep() -> str:
    """PyInstaller path separator (: on Unix, ; on Windows)."""
    return ";" if platform.system() == "Windows" else ":"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build shenas binaries with PyInstaller")
    parser.add_argument("targets", nargs="*", help="Targets to build (default: all)")
    parser.add_argument("--list", action="store_true", help="List available targets")
    parser.add_argument(
        "--desktop",
        action="store_true",
        help="Build --onefile binaries into app/desktop/src-tauri/binaries/ for Tauri sidecar bundling",
    )
    args = parser.parse_args()

    if args.list:
        for name, target in TARGETS.items():
            print(f"  {name:20s} {target['description']}")
        return

    to_build = args.targets or list(TARGETS.keys())
    for name in to_build:
        if name not in TARGETS:
            print(f"Unknown target: {name}")
            print(f"Available: {', '.join(TARGETS)}")
            sys.exit(1)

    # Verify PyInstaller is available
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("PyInstaller not found. Install it with: uv add --dev pyinstaller")
        sys.exit(1)

    onefile = args.desktop
    dist_dir = DESKTOP_BIN_DIR if args.desktop else DIST_DIR

    # For --onefile on Linux, create a patched copy of libpython
    patched_libpython = None
    if onefile and platform.system() == "Linux":
        print("Preparing patched libpython for --onefile compatibility...")
        patched_libpython = _patch_source_libpython()

    dist_dir.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for name in to_build:
        results[name] = build_target(
            name, TARGETS[name], onefile=onefile, dist_dir=dist_dir, patched_libpython=patched_libpython
        )

    print(f"\n{'=' * 60}")
    print("Build complete!")
    print(f"{'=' * 60}")
    for name, path in results.items():
        status = "OK" if path.exists() else "MISSING"
        print(f"  {name:20s} {status:8s} {path}")


if __name__ == "__main__":
    main()
