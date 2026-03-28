"""Sync version to desktop config files (tauri.conf.json, Cargo.toml, package.json, PKGBUILD).

Reads version from argument, or from the latest desktop/v* git tag.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESKTOP = ROOT / "app" / "desktop"


def version_from_git() -> str:
    """Get version from the latest desktop/v* tag."""
    result = subprocess.run(
        ["git", "describe", "--tags", "--match", "desktop/v*", "--abbrev=0"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    if result.returncode != 0:
        return "0.0.0"
    return result.stdout.strip().removeprefix("desktop/v")


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else version_from_git()

    # tauri.conf.json
    tauri_conf = DESKTOP / "src-tauri" / "tauri.conf.json"
    conf = json.loads(tauri_conf.read_text())
    conf["version"] = version
    tauri_conf.write_text(json.dumps(conf, indent=2) + "\n")

    # Cargo.toml -- only the [package] version line
    cargo = DESKTOP / "src-tauri" / "Cargo.toml"
    lines = cargo.read_text().splitlines(keepends=True)
    in_package = False
    for i, line in enumerate(lines):
        if line.strip() == "[package]":
            in_package = True
        elif line.startswith("[") and in_package:
            in_package = False
        elif in_package and line.startswith("version = "):
            lines[i] = f'version = "{version}"\n'
            break
    cargo.write_text("".join(lines))

    # package.json
    pkg_json = DESKTOP / "package.json"
    pkg = json.loads(pkg_json.read_text())
    pkg["version"] = version
    pkg_json.write_text(json.dumps(pkg, indent=2) + "\n")

    # PKGBUILD
    pkgbuild = DESKTOP / "PKGBUILD"
    text = pkgbuild.read_text()
    text = re.sub(r"^pkgver=.*$", f"pkgver={version}", text, flags=re.MULTILINE)
    pkgbuild.write_text(text)

    print(f"Synced desktop version to {version}")


if __name__ == "__main__":
    main()
