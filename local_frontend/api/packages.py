"""Package management API endpoints."""

import json
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cli.commands.pkg import DEFAULT_INDEX, PREFIXES, PUBLIC_KEY_PATH, check_signature

router = APIRouter(prefix="/packages", tags=["packages"])

VALID_KINDS = {"pipe", "schema", "component"}


def _validate_kind(kind: str) -> None:
    if kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail=f"Invalid kind: {kind}. Must be one of: {', '.join(sorted(VALID_KINDS))}")


def list_packages_data(kind: str) -> list[dict]:
    prefix = PREFIXES[kind]
    result = subprocess.run(["uv", "pip", "list", "--format", "json"], capture_output=True, text=True)
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


def install_package(
    name: str,
    kind: str,
    index_url: str = DEFAULT_INDEX,
    public_key_path: Path = PUBLIC_KEY_PATH,
    skip_verify: bool = False,
) -> dict:
    if name == "core":
        return {"name": name, "ok": False, "message": f"shenas-{kind}-core is an internal package"}

    prefix = PREFIXES[kind]
    pkg_name = f"{prefix}{name}"

    if not skip_verify:
        if not public_key_path.exists():
            return {"name": name, "ok": False, "message": f"Public key not found at {public_key_path}"}
        from cli.commands.pkg import _verify_from_index
        from repository.signing import load_public_key

        pub_key = load_public_key(public_key_path)
        try:
            _verify_from_index(pkg_name, index_url, pub_key)
        except SystemExit:
            return {"name": name, "ok": False, "message": "Signature verification failed"}

    simple_url = f"{index_url}/simple/"
    result = subprocess.run(
        ["uv", "pip", "install", pkg_name, "--index-url", simple_url],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        return {"name": name, "ok": True, "message": f"Installed {pkg_name}"}
    return {"name": name, "ok": False, "message": result.stderr.strip() or f"Failed to install {pkg_name}"}


def uninstall_package(name: str, kind: str) -> dict:
    if name == "core":
        return {"ok": False, "message": f"shenas-{kind}-core is an internal package"}

    pkg_name = f"{PREFIXES[kind]}{name}"
    result = subprocess.run(["uv", "pip", "uninstall", pkg_name], capture_output=True, text=True)

    if result.returncode == 0:
        return {"ok": True, "message": f"Uninstalled {pkg_name}"}
    return {"ok": False, "message": result.stderr.strip() or f"Failed to uninstall {pkg_name}"}


@router.get("/{kind}")
def list_pkgs(kind: str) -> list[dict]:
    _validate_kind(kind)
    return list_packages_data(kind)


class InstallRequest(BaseModel):
    names: list[str]
    index_url: str | None = None
    skip_verify: bool = False


@router.post("/{kind}")
def add_pkgs(kind: str, body: InstallRequest) -> dict:
    _validate_kind(kind)
    results = []
    for name in body.names:
        results.append(install_package(name, kind, index_url=body.index_url or DEFAULT_INDEX, skip_verify=body.skip_verify))
    return {"results": results}


@router.delete("/{kind}/{name}")
def remove_pkg(kind: str, name: str) -> dict:
    _validate_kind(kind)
    return uninstall_package(name, kind)
