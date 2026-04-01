"""Build standalone binaries for shenas using PyInstaller.

Usage:
    uv run python build/pyinstaller_build.py                  # build all
    uv run python build/pyinstaller_build.py shenas            # build one
    uv run python build/pyinstaller_build.py --list            # list targets
"""

from __future__ import annotations

import argparse
import importlib.metadata
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist" / "pyinstaller"
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


def _patch_execstack(internal_dir: Path) -> None:
    """Clear the executable stack flag (PF_X) from ELF shared libraries.

    Linux kernel 6.x enforces W^X and refuses to load .so files with
    GNU_STACK marked RWE. Some Python builds (e.g. proto/python) have this
    flag set. We patch the ELF program header in-place to clear PF_X.
    """
    import struct

    PT_GNU_STACK = 0x6474E551
    PF_X = 0x1

    for so_file in internal_dir.glob("*.so*"):
        try:
            with open(so_file, "r+b") as f:
                ident = f.read(16)
                if ident[:4] != b"\x7fELF" or ident[4] != 2:  # only 64-bit ELF
                    continue

                f.seek(32)  # e_phoff
                phoff = struct.unpack("<Q", f.read(8))[0]
                f.seek(54)  # e_phentsize, e_phnum
                phentsize = struct.unpack("<H", f.read(2))[0]
                phnum = struct.unpack("<H", f.read(2))[0]

                for i in range(phnum):
                    off = phoff + i * phentsize
                    f.seek(off)
                    p_type = struct.unpack("<I", f.read(4))[0]
                    if p_type == PT_GNU_STACK:
                        f.seek(off + 4)
                        p_flags = struct.unpack("<I", f.read(4))[0]
                        if p_flags & PF_X:
                            f.seek(off + 4)
                            f.write(struct.pack("<I", p_flags & ~PF_X))
                            print(f"  Patched {so_file.name}: cleared executable stack flag")
                        break
        except Exception:
            pass  # skip files we can't patch


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


def build_target(name: str, target: dict[str, Path | str]) -> Path:
    """Build a single PyInstaller target. Returns the output path."""
    triple = _target_triple()
    output_name = f"{name}-{triple}"

    print(f"\n{'=' * 60}")
    print(f"Building {name} ({target['description']})")
    print(f"{'=' * 60}\n")

    sep = _sep()
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onedir",
        f"--name={output_name}",
        f"--distpath={DIST_DIR}",
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

    # --onedir places the binary inside a directory of the same name
    output_path = DIST_DIR / output_name / output_name
    if platform.system() == "Windows":
        output_path = output_path.with_suffix(".exe")

    print(f"\nBuilt: {output_path}")
    if output_path.exists():
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"Size: {size_mb:.1f} MB")
        # Total directory size
        dir_path = output_path.parent
        total = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
        print(f"Total directory: {total / (1024 * 1024):.1f} MB")
        # Patch executable stack on Linux (kernel 6.x blocks RWE stacks)
        if platform.system() == "Linux":
            _patch_execstack(output_path.parent / "_internal")

    return output_path


def _sep() -> str:
    """PyInstaller path separator (: on Unix, ; on Windows)."""
    return ";" if platform.system() == "Windows" else ":"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build shenas binaries with PyInstaller")
    parser.add_argument("targets", nargs="*", help="Targets to build (default: all)")
    parser.add_argument("--list", action="store_true", help="List available targets")
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

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    results = {}
    for name in to_build:
        results[name] = build_target(name, TARGETS[name])

    print(f"\n{'=' * 60}")
    print("Build complete!")
    print(f"{'=' * 60}")
    for name, path in results.items():
        status = "OK" if path.exists() else "MISSING"
        print(f"  {name:20s} {status:8s} {path}")


if __name__ == "__main__":
    main()
