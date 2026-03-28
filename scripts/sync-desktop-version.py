"""Sync app/VERSION to desktop config files (tauri.conf.json, Cargo.toml, package.json, PKGBUILD)."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_VERSION = ROOT / "app" / "VERSION"
DESKTOP = ROOT / "app" / "desktop"


def main() -> None:
    version = APP_VERSION.read_text().strip()
    if len(sys.argv) > 1:
        version = sys.argv[1]
        APP_VERSION.write_text(version + "\n")

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

    print(f"Synced version to {version}")


if __name__ == "__main__":
    main()
