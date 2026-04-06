"""Build standalone binaries for shenas using PyInstaller.

Usage:
    uv run python build/pyinstaller_build.py                  # build all (onedir, shared _internal)
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
WORK_DIR = ROOT / "build" / "_pyinstaller_work"


# ---- Per-target hidden imports ----
# Only include what each target actually needs. The server is the fattest
# (full app + plugins + telemetry). The CLI needs commands but not uvicorn.
# The scheduler only needs httpx + typer.

_IMPORTS_SHARED = [
    "shenasctl.client",
    "jaraco.text",
    "jaraco.functools",
    "jaraco.context",
]

_IMPORTS_SERVER = [
    "app",
    "app.server",
    "app.server_cli",
    "app.api",
    "app.api.db",
    "app.api.plugins",
    "app.api.sync",
    "app.api.transforms",
    "app.cli",
    "shenasctl.main",
    "shenasctl.client",
    "shenasctl.commands",
    "shenasctl.commands.pipe",
    "shenasctl.commands.component",
    "shenasctl.commands.config_cmd",
    "shenasctl.commands.db_cmd",
    "shenasctl.commands.schema_cmd",
    "shenasctl.commands.service",
    "shenasctl.commands.theme_cmd",
    "shenasctl.commands.transform_cmd",
    "shenasctl.commands.ui_cmd",
    "app.db",
    "app.transforms",
    "app.telemetry",
    "app.telemetry.setup",
    "app.telemetry.exporters",
    "app.telemetry.dispatcher",
    "app.telemetry.schema",
    "repository",
    # Internal/bundled plugin packages (user plugins installed separately)
    "shenas_sources",
    "shenas_sources.core",
    "shenas_datasets",
    "shenas_datasets.core",
    "shenas_frontends",
    "shenas_frontends.default",
    "shenas_themes",
    "shenas_themes.default",
    # Dependencies with dynamic imports
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

_IMPORTS_CLI = [
    "app.cli",
    "shenasctl.main",
    "shenasctl.client",
    "shenasctl.commands",
    "shenasctl.commands.pipe",
    "shenasctl.commands.component",
    "shenasctl.commands.config_cmd",
    "shenasctl.commands.db_cmd",
    "shenasctl.commands.schema_cmd",
    "shenasctl.commands.service",
    "shenasctl.commands.theme_cmd",
    "shenasctl.commands.transform_cmd",
    "shenasctl.commands.ui_cmd",
]

_IMPORTS_SCHEDULER = [
    "scheduler",
    "scheduler.cli",
    "scheduler.daemon",
    "shenasctl.client",
]

# Modules to exclude globally
_EXCLUDES_GLOBAL = [
    "pytest",
    "_pytest",
    "py",
    "pip",
    "distutils",
    "tkinter",
    "unittest",
    "xmlrpc",
    "pydoc",
    "doctest",
]

# Extra excludes for lightweight targets (scheduler/CLI don't need these)
_EXCLUDES_LIGHTWEIGHT = [
    "pyarrow",
    "numpy",
    "pandas",
    "uvicorn",
    "fastapi",
    "starlette",
    "opentelemetry",
    "dlt",
    "pendulum",
    "fsspec",
    "google",
    "googleapiclient",
    "google_auth_httplib2",
    "httplib2",
]

# Extra excludes for CLI (doesn't need server runtime)
_EXCLUDES_CLI = [
    "duckdb",
    "dlt",
    "pyarrow",
    "numpy",
    "pandas",
    "uvicorn",
    "fastapi",
    "starlette",
    "opentelemetry",
    "pendulum",
    "fsspec",
    "google",
    "googleapiclient",
    "google_auth_httplib2",
    "httplib2",
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


# Internal packages to include in dist-info. Non-internal plugins (garmin,
# fitness-dashboard, etc.) are installed separately by the user.
_INTERNAL_PACKAGES = {
    "shenas-app",
    "shenas-scheduler",
    "shenas-source-core",
    "shenas-dataset-core",
    "shenas-frontend-default",
    "shenas-theme-default",
    "dlt",
    "duckdb",
}


def _collect_dist_info_datas(target_name: str) -> list[tuple[str, str]]:
    """Collect .dist-info directories so importlib.metadata.entry_points() works at runtime."""
    datas: list[tuple[str, str]] = []
    # Scheduler only needs its own dist-info + shenas-app (for the client)
    scheduler_only = {"shenas-scheduler", "shenas-app"}

    for dist in importlib.metadata.distributions():
        name = dist.metadata["Name"] or ""
        if name not in _INTERNAL_PACKAGES:
            continue
        if target_name == "shenas-scheduler" and name not in scheduler_only:
            continue
        if dist._path and dist._path.exists():
            datas.append((str(dist._path), dist._path.name))
    return datas


def _collect_package_datas(target_name: str) -> list[str]:
    """Packages whose non-.py data files (JSON, CSS, HTML, static) must be included.

    Only internal packages are bundled. User plugins (pipes, schemas,
    components, themes, UI) are installed separately via shenasctl.
    """
    if target_name == "shenas-scheduler":
        return []
    return [
        "shenas_sources.core",
        "shenas_datasets.core",
        "shenas_frontends.default",
        "shenas_themes.default",
    ]


def _collect_explicit_datas(target_name: str) -> list[tuple[str, str]]:
    """Specific data files from app/ that are needed at runtime."""
    if target_name == "shenas-scheduler":
        return []
    datas: list[tuple[str, str]] = []
    static_dir = ROOT / "app" / "static"
    if static_dir.is_dir():
        datas.append((str(static_dir), "app/static"))
    vendor_dir = ROOT / "app" / "vendor" / "dist"
    if vendor_dir.is_dir():
        datas.append((str(vendor_dir), "app/vendor/dist"))
    return datas


def _get_hidden_imports(target_name: str) -> list[str]:
    """Return hidden imports for a specific target."""
    if target_name == "shenas":
        return _IMPORTS_SERVER
    if target_name == "shenasctl":
        return _IMPORTS_CLI
    if target_name == "shenas-scheduler":
        return _IMPORTS_SCHEDULER
    return _IMPORTS_SERVER  # fallback to full


def _get_excludes(target_name: str) -> list[str]:
    """Return module exclusions for a specific target."""
    excludes = list(_EXCLUDES_GLOBAL)
    if target_name == "shenas-scheduler":
        excludes.extend(_EXCLUDES_LIGHTWEIGHT)
    elif target_name == "shenasctl":
        excludes.extend(_EXCLUDES_CLI)
    return excludes


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

    try:
        result = subprocess.run(["ldd", str(python_bin)], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if "libpython" in line and "=>" in line:
                parts = line.strip().split("=>")
                if len(parts) == 2:
                    path = parts[1].strip().split("(")[0].strip()
                    if path and Path(path).exists():
                        return Path(path)
    except Exception:
        pass

    python_home = python_bin.parent.parent / "lib"
    for candidate in python_home.glob("libpython*.so*"):
        if candidate.is_file() and not candidate.is_symlink():
            return candidate

    return None


def _patch_source_libpython() -> Path | None:  # noqa: PLR0911
    """Create a patched copy of libpython with executable stack flag cleared."""
    if platform.system() != "Linux":
        return None

    libpython = _find_libpython()
    if libpython is None:
        print("  WARNING: Could not locate libpython shared library")
        return None

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
    hidden_imports = _get_hidden_imports(name)
    excludes = _get_excludes(name)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile" if onefile else "--onedir",
        f"--name={output_name}",
        f"--distpath={dist_dir}",
        f"--workpath={WORK_DIR / name}",
        f"--specpath={WORK_DIR}",
        # Strip debug symbols from shared libraries
        "--strip",
        # Hidden imports (target-specific)
        *[f"--hidden-import={mod}" for mod in hidden_imports],
        # Package data (target-specific)
        *[f"--collect-data={pkg}" for pkg in _collect_package_datas(name)],
        # Explicit data files
        *[f"--add-data={src}{sep}{dest}" for src, dest in _collect_explicit_datas(name)],
        # .dist-info directories for importlib.metadata (target-specific)
        *[f"--add-data={src}{sep}{dest}" for src, dest in _collect_dist_info_datas(name)],
        # Override bundled libpython with patched copy (execstack fix)
        *([f"--add-binary={patched_libpython}{sep}."] if patched_libpython else []),
        # No UPX (adds startup latency)
        "--noupx",
        # Module exclusions (target-specific)
        *[f"--exclude-module={mod}" for mod in excludes],
        # Search path
        f"--paths={ROOT}",
        # Clean build
        "--clean",
        "--noconfirm",
        str(target["entry"]),
    ]

    print(f"Running PyInstaller with {len(cmd)} args...")
    print(f"  Hidden imports: {len(hidden_imports)}, Excludes: {len(excludes)}")
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
            if platform.system() == "Linux":
                _patch_execstack_dir(output_path.parent / "_internal")

    return output_path


def _merge_onedir_outputs(dist_dir: Path, built_targets: dict[str, Path]) -> None:
    """Merge multiple --onedir builds into a shared directory.

    PyInstaller --onedir creates <name>/<name> + <name>/_internal/ per target.
    Since all targets share the same Python runtime and many of the same
    libraries, we merge them into a single directory with one _internal/.
    """
    if len(built_targets) < 2:
        return

    triple = _target_triple()
    shared_dir = dist_dir / f"shenas-{triple}"
    shared_internal = shared_dir / "_internal"

    print(f"\n{'=' * 60}")
    print(f"Merging {len(built_targets)} targets into {shared_dir}")
    print(f"{'=' * 60}\n")

    # Use the fattest target's _internal as the base
    fattest_name = "shenas"  # server has the most deps
    fattest_path = built_targets.get(fattest_name)
    if not fattest_path:
        fattest_path = next(iter(built_targets.values()))

    fattest_dir = fattest_path.parent
    fattest_internal = fattest_dir / "_internal"

    # Create shared directory and move the fattest _internal
    shared_dir.mkdir(parents=True, exist_ok=True)
    if shared_internal.exists():
        shutil.rmtree(shared_internal)
    shutil.move(str(fattest_internal), str(shared_internal))

    # Copy the fattest executable
    shutil.copy2(fattest_path, shared_dir / fattest_path.name)

    # Merge other targets: copy their _internal files (fills gaps) and executables
    for path in built_targets.values():
        if path == fattest_path:
            continue
        target_dir = path.parent
        target_internal = target_dir / "_internal"

        # Copy any files from this target's _internal that aren't in the shared one
        if target_internal.exists():
            for src_file in target_internal.rglob("*"):
                if src_file.is_file():
                    rel = src_file.relative_to(target_internal)
                    dest = shared_internal / rel
                    if not dest.exists():
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_file, dest)

        # Copy the executable
        shutil.copy2(path, shared_dir / path.name)

    # Clean up individual target directories
    for path in built_targets.values():
        target_dir = path.parent
        if target_dir != shared_dir and target_dir.exists():
            shutil.rmtree(target_dir)

    # Report sizes
    total = sum(f.stat().st_size for f in shared_dir.rglob("*") if f.is_file())
    executables = [f for f in shared_dir.iterdir() if f.is_file() and not f.name.startswith(".")]
    print(f"Shared directory: {total / (1024 * 1024):.1f} MB")
    print(f"Executables: {', '.join(f.name for f in executables)}")


def _sep() -> str:
    """PyInstaller path separator (: on Unix, ; on Windows)."""
    return ";" if platform.system() == "Windows" else ":"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build shenas binaries with PyInstaller")
    parser.add_argument("targets", nargs="*", help="Targets to build (default: all)")
    parser.add_argument("--list", action="store_true", help="List available targets")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Build single-file binaries (for Tauri sidecars). Default is --onedir.",
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

    onefile = args.onefile
    dist_dir = DIST_DIR

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
            name,
            TARGETS[name],
            onefile=onefile,
            dist_dir=dist_dir,
            patched_libpython=patched_libpython,
        )

    # For --onedir with multiple targets, merge into shared directory
    if not onefile and len(results) > 1:
        _merge_onedir_outputs(dist_dir, results)

    print(f"\n{'=' * 60}")
    print("Build complete!")
    print(f"{'=' * 60}")
    for name, path in results.items():
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  {name:20s} {size_mb:>7.1f} MB  {path}")
        else:
            print(f"  {name:20s} {'MISSING':>7s}  {path}")


if __name__ == "__main__":
    main()
