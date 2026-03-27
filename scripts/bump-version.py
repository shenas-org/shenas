#!/usr/bin/env python3
"""Bump patch version only if source files changed since last build.

Usage: python scripts/bump-version.py <VERSION_FILE>

Computes a hash of all source files in the package directory (parent of VERSION).
If unchanged since last build, prints the current version and exits with code 1
(signals the Makefile to skip the build). If changed, bumps the patch version,
writes it back, saves the new hash, and prints the new version (exit 0).
"""

import hashlib
import sys
from pathlib import Path

HASH_DIR = Path(".build-hashes")
SKIP_NAMES = {"__pycache__", "node_modules", "dist", ".build-hashes", "static"}
SKIP_SUFFIXES = {".pyc"}
SKIP_FILES = {"VERSION", "package.json", "package-lock.json"}


def _source_hash(pkg_dir: Path) -> str:
    """Compute a single hash of all source files in a directory."""
    h = hashlib.sha256()
    for f in sorted(pkg_dir.rglob("*")):
        if not f.is_file():
            continue
        if any(part in SKIP_NAMES for part in f.parts):
            continue
        if f.suffix in SKIP_SUFFIXES or f.name in SKIP_FILES:
            continue
        h.update(str(f.relative_to(pkg_dir)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def main() -> None:
    version_file = Path(sys.argv[1])
    pkg_dir = version_file.parent
    current_version = version_file.read_text().strip()

    # Compute source hash
    current_hash = _source_hash(pkg_dir)

    # Check stored hash
    HASH_DIR.mkdir(parents=True, exist_ok=True)
    hash_key = str(pkg_dir).replace("/", "_").replace("\\", "_")
    hash_file = HASH_DIR / hash_key

    if hash_file.exists() and hash_file.read_text().strip() == current_hash:
        # Unchanged — print current version and signal skip
        print(current_version)
        sys.exit(1)

    # Changed — bump patch version
    parts = current_version.split(".")
    parts[2] = str(int(parts[2]) + 1)
    new_version = ".".join(parts)
    version_file.write_text(new_version + "\n")

    # Save hash
    hash_file.write_text(current_hash + "\n")

    print(new_version)


if __name__ == "__main__":
    main()
