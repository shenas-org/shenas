"""Package management API endpoints."""

from __future__ import annotations

import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.cli.commands.pkg import DEFAULT_INDEX, PREFIXES, PUBLIC_KEY_PATH, check_signature
from repository.signing import load_public_key, verify_bytes

router = APIRouter(prefix="/packages", tags=["packages"])

VALID_KINDS = {"pipe", "schema", "component"}


def _validate_kind(kind: str) -> None:
    if kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail=f"Invalid kind: {kind}. Must be one of: {', '.join(sorted(VALID_KINDS))}")


def list_packages_data(kind: str) -> list[dict[str, str]]:
    import sys

    prefix = PREFIXES[kind]
    result = subprocess.run(
        ["uv", "pip", "list", "--format", "json", "--python", sys.executable], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail="Failed to list packages")

    packages = json.loads(result.stdout)
    matched = [p for p in packages if p["name"].startswith(prefix) and not p["name"].endswith("-core")]

    items = []
    for p in sorted(matched, key=lambda x: x["name"]):
        short_name = p["name"].removeprefix(prefix)
        sig_status = check_signature(p["name"], p["version"])
        items.append({"name": short_name, "package": p["name"], "version": p["version"], "signature": sig_status})
    return items


def _verify_from_index(pkg_name: str, index_url: str, pub_key: Ed25519PublicKey) -> str | None:
    """Verify a package signature from the index. Returns error message or None on success."""
    normalized = pkg_name.replace("_", "-").lower()
    simple_pkg_url = f"{index_url}/simple/{normalized}/"
    try:
        with urlopen(simple_pkg_url) as resp:
            html = resp.read().decode()
    except Exception as exc:
        return f"Cannot reach repository: {exc}"

    wheel_href = None

    class LinkParser(HTMLParser):
        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            nonlocal wheel_href
            if tag == "a":
                for attr_name, attr_val in attrs:
                    if attr_name == "href" and attr_val and ".whl" in attr_val:
                        wheel_href = attr_val.split("#")[0]

    LinkParser().feed(html)

    if not wheel_href:
        return f"No wheel found for {pkg_name} in repository"

    wheel_url = f"{index_url}{wheel_href}" if wheel_href.startswith("/") else f"{index_url}/{wheel_href}"
    sig_url = f"{wheel_url}.sig"

    try:
        with urlopen(sig_url) as resp:
            sig_b64 = resp.read().decode().strip()
    except Exception:
        return f"No signature found for {pkg_name}"

    try:
        with urlopen(wheel_url) as resp:
            wheel_bytes = resp.read()
    except Exception as exc:
        return f"Cannot download wheel: {exc}"

    if not verify_bytes(pub_key, wheel_bytes, sig_b64):
        return f"SIGNATURE VERIFICATION FAILED for {pkg_name}"

    return None


def install_package(
    name: str,
    kind: str,
    index_url: str = DEFAULT_INDEX,
    public_key_path: Path = PUBLIC_KEY_PATH,
    skip_verify: bool = False,
) -> dict[str, object]:
    if name == "core":
        return {"name": name, "ok": False, "message": f"shenas-{kind}-core is an internal package"}

    prefix = PREFIXES[kind]
    pkg_name = f"{prefix}{name}"

    if not skip_verify:
        if not public_key_path.exists():
            return {"name": name, "ok": False, "message": f"Public key not found at {public_key_path}"}
        pub_key = load_public_key(public_key_path)
        error = _verify_from_index(pkg_name, index_url, pub_key)
        if error:
            return {"name": name, "ok": False, "message": error}

    import sys

    simple_url = f"{index_url}/simple/"
    result = subprocess.run(
        ["uv", "pip", "install", pkg_name, "--index-url", simple_url, "--python", sys.executable],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return {"name": name, "ok": True, "message": f"Installed {pkg_name}"}
    return {"name": name, "ok": False, "message": result.stderr.strip() or f"Failed to install {pkg_name}"}


def uninstall_package(name: str, kind: str) -> dict[str, object]:
    import sys

    if name == "core":
        return {"ok": False, "message": f"shenas-{kind}-core is an internal package"}

    pkg_name = f"{PREFIXES[kind]}{name}"
    result = subprocess.run(["uv", "pip", "uninstall", pkg_name, "--python", sys.executable], capture_output=True, text=True)

    if result.returncode == 0:
        return {"ok": True, "message": f"Uninstalled {pkg_name}"}
    return {"ok": False, "message": result.stderr.strip() or f"Failed to uninstall {pkg_name}"}


@router.get("/{kind}")
def list_pkgs(kind: str) -> list[dict[str, str]]:
    _validate_kind(kind)
    return list_packages_data(kind)


class InstallRequest(BaseModel):
    names: list[str]
    index_url: str | None = None
    skip_verify: bool = False


@router.post("/{kind}")
def add_pkgs(kind: str, body: InstallRequest) -> dict[str, list[dict[str, object]]]:
    _validate_kind(kind)
    results = []
    for name in body.names:
        results.append(install_package(name, kind, index_url=body.index_url or DEFAULT_INDEX, skip_verify=body.skip_verify))
    return {"results": results}


@router.delete("/{kind}/{name}")
def remove_pkg(kind: str, name: str) -> dict[str, object]:
    _validate_kind(kind)
    return uninstall_package(name, kind)
