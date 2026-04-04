"""Plugin management API endpoints."""

from __future__ import annotations

import importlib
import json
import logging
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, HTTPException

from app.db import get_plugin_state
from app.models import InstallRequest, InstallResponse, InstallResult, OkResponse, PluginInfo, RemoveResponse

router = APIRouter(prefix="/plugins", tags=["plugins"])

log = logging.getLogger(f"shenas.{__name__}")

DEFAULT_INDEX = "http://127.0.0.1:7290"
PACKAGES_DIR = Path(__file__).resolve().parent.parent.parent / "packages"
PUBLIC_KEY_PATH = Path(".shenas") / "shenas.pub"

VALID_KINDS = {"pipe", "schema", "component", "ui", "theme"}


def _prefix(kind: str) -> str:
    return f"shenas-{kind}-"


NAMESPACES = {
    "pipe": "shenas_pipes",
    "schema": "shenas_schemas",
    "component": "shenas_components",
    "ui": "shenas_ui",
    "theme": "shenas_themes",
}

# Standard metadata dict names exported by each plugin type
_META_ATTRS = ("COMPONENT", "UI", "SCHEMA", "PLUGIN", "THEME")


def _validate_kind(kind: str) -> None:
    if kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail=f"Invalid kind: {kind}. Must be one of: {', '.join(sorted(VALID_KINDS))}")


def _is_internal(kind: str, name: str) -> bool:
    """Check if a plugin is internal (hidden from list/add/remove/UI)."""
    if name == "core":
        return True
    namespace = NAMESPACES.get(kind)
    if not namespace:
        return False
    try:
        mod = importlib.import_module(f"{namespace}.{name}")
        for attr in _META_ATTRS:
            meta = getattr(mod, attr, None)
            if isinstance(meta, dict) and meta.get("internal"):
                return True
    except (ImportError, ModuleNotFoundError):
        pass
    return False


def _load_public_key(path: Path) -> Ed25519PublicKey:
    """Load an Ed25519 public key from a PEM file."""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    key = load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError(f"Expected Ed25519 public key, got {type(key)}")
    return key


def _verify_file(public_key: Ed25519PublicKey, file_path: Path, sig_b64: str) -> bool:
    """Verify a file against a base64-encoded Ed25519 signature."""
    import base64

    try:
        public_key.verify(base64.b64decode(sig_b64), file_path.read_bytes())
        return True
    except Exception:
        return False


def _verify_bytes(public_key: Ed25519PublicKey, data: bytes, sig_b64: str) -> bool:
    """Verify raw bytes against a base64-encoded Ed25519 signature."""
    import base64

    try:
        public_key.verify(base64.b64decode(sig_b64), data)
        return True
    except Exception:
        return False


def check_signature(pkg_name: str, version: str) -> str:
    """Check if a package wheel has a valid Ed25519 signature."""
    if not PUBLIC_KEY_PATH.exists():
        return "no key"

    normalized = pkg_name.replace("-", "_")
    matches = list(PACKAGES_DIR.glob(f"{normalized}-{version}*.whl")) if PACKAGES_DIR.is_dir() else []
    if not matches:
        return "unsigned"

    wheel_path = matches[0]
    sig_path = wheel_path.with_suffix(wheel_path.suffix + ".sig")
    if not sig_path.exists():
        return "unsigned"

    pub_key = _load_public_key(PUBLIC_KEY_PATH)
    return "valid" if _verify_file(pub_key, wheel_path, sig_path.read_text().strip()) else "invalid"


def _pipe_status(name: str) -> tuple[bool | None, int | None]:
    """Check if a pipe has auth credentials and its sync frequency."""
    from app.api.pipes import _load_pipe
    from shenas_pipes.core.base_config import PipeConfig
    from shenas_pipes.core.store import DataclassStore

    has_auth = None
    sync_freq = None

    try:
        pipe = _load_pipe(name)
    except Exception:
        return None, None

    # Check auth
    if not pipe.has_auth:
        has_auth = True  # no auth needed
    else:
        try:
            _auth = DataclassStore("auth")
            row = _auth.get(pipe.Auth)
            has_auth = bool(row and any(v for k, v in row.items() if k != "id"))
        except Exception:
            has_auth = None

    # Check sync frequency from config
    if pipe.Config is not PipeConfig:
        try:
            _config = DataclassStore("config")
            row = _config.get(pipe.Config)
            if row:
                sync_freq = row.get("sync_frequency")
        except Exception:
            pass

    return has_auth, sync_freq


def list_plugins_data(kind: str) -> list[PluginInfo]:
    import sys

    prefix = _prefix(kind)
    result = subprocess.run(
        ["uv", "pip", "list", "--format", "json", "--python", sys.executable], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail="Failed to list plugins")

    installed = json.loads(result.stdout)
    matched = [p for p in installed if p["name"].startswith(prefix)]

    items = []
    for p in sorted(matched, key=lambda x: x["name"]):
        short_name = p["name"].removeprefix(prefix)
        if _is_internal(kind, short_name):
            continue
        sig_status = check_signature(p["name"], p["version"])
        display = _plugin_display_name(kind, short_name)
        desc = _plugin_description(kind, short_name)
        cmds = _plugin_commands(kind, short_name)
        state = get_plugin_state(kind, short_name)

        has_auth = None
        sync_freq = None
        if kind == "pipe":
            has_auth, sync_freq = _pipe_status(short_name)

        items.append(
            PluginInfo(
                name=short_name,
                display_name=display,
                package=p["name"],
                version=p["version"],
                signature=sig_status,
                description=desc,
                commands=cmds,
                enabled=state["enabled"] if state else (kind not in _EXCLUSIVE_KINDS),
                has_auth=has_auth,
                sync_frequency=sync_freq,
                added_at=state["added_at"] if state else None,
                updated_at=state["updated_at"] if state else None,
                status_changed_at=state["status_changed_at"] if state else None,
                synced_at=state["synced_at"] if state else None,
            )
        )
    return items


def _verify_from_index(pkg_name: str, index_url: str, pub_key: Ed25519PublicKey) -> str | None:
    """Verify a plugin signature from the index. Returns error message or None on success."""
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

    if not _verify_bytes(pub_key, wheel_bytes, sig_b64):
        return f"SIGNATURE VERIFICATION FAILED for {pkg_name}"

    return None


def install_plugin(
    name: str,
    kind: str,
    index_url: str = DEFAULT_INDEX,
    public_key_path: Path = PUBLIC_KEY_PATH,
    skip_verify: bool = False,
) -> InstallResult:
    if _is_internal(kind, name):
        return InstallResult(name=name, ok=False, message=f"shenas-{kind}-{name} is an internal plugin")

    prefix = _prefix(kind)
    pkg_name = f"{prefix}{name}"

    if not skip_verify:
        if not public_key_path.exists():
            return InstallResult(name=name, ok=False, message=f"Public key not found at {public_key_path}")
        pub_key = _load_public_key(public_key_path)
        error = _verify_from_index(pkg_name, index_url, pub_key)
        if error:
            return InstallResult(name=name, ok=False, message=error)

    import sys

    simple_url = f"{index_url}/simple/"
    result = subprocess.run(
        ["uv", "pip", "install", pkg_name, "--index-url", simple_url, "--python", sys.executable],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        from app.db import upsert_plugin_state

        upsert_plugin_state(kind, name, enabled=True)
        return InstallResult(name=name, ok=True, message=f"Installed {pkg_name}")
    return InstallResult(name=name, ok=False, message=result.stderr.strip() or f"Failed to install {pkg_name}")


def uninstall_plugin(name: str, kind: str) -> RemoveResponse:
    import sys

    if _is_internal(kind, name):
        return RemoveResponse(ok=False, message=f"shenas-{kind}-{name} is an internal plugin")

    pkg_name = f"{_prefix(kind)}{name}"
    result = subprocess.run(["uv", "pip", "uninstall", pkg_name, "--python", sys.executable], capture_output=True, text=True)

    if result.returncode == 0:
        from app.db import remove_plugin_state

        remove_plugin_state(kind, name)
        return RemoveResponse(ok=True, message=f"Uninstalled {pkg_name}")
    return RemoveResponse(ok=False, message=result.stderr.strip() or f"Failed to uninstall {pkg_name}")


def _plugin_commands(kind: str, name: str) -> list[str]:
    """Detect available commands for a plugin."""
    commands = ["describe"]

    if kind != "pipe":
        return commands

    from app.api.pipes import _load_pipe

    try:
        pipe = _load_pipe(name)
        return pipe.commands
    except Exception:
        commands.append("sync")
        return commands


def _load_plugin_module(kind: str, name: str) -> Any:
    """Try to import a plugin module (cli first, then __init__)."""
    namespace = NAMESPACES[kind]
    py_name = name.replace("-", "_")
    for mod_suffix in ("cli", ""):
        mod_name = f"{namespace}.{py_name}.{mod_suffix}".rstrip(".")
        try:
            return importlib.import_module(mod_name)
        except (ImportError, ModuleNotFoundError):
            continue
    return None


def _plugin_display_name(kind: str, name: str) -> str:
    """Load a human-readable display name from a plugin."""
    if kind == "pipe":
        from app.api.pipes import _load_pipe

        try:
            return _load_pipe(name).display_name
        except Exception:
            pass

    mod = _load_plugin_module(kind, name)
    if mod:
        for attr in ("DISPLAY_NAME", "PIPE_DISPLAY_NAME"):
            val = getattr(mod, attr, None)
            if val:
                return val
        for attr in _META_ATTRS:
            meta = getattr(mod, attr, None)
            if isinstance(meta, dict) and meta.get("display_name"):
                return meta["display_name"]
            if isinstance(meta, type) and hasattr(meta, "display_name"):
                return meta.display_name
    return ""


def _plugin_description(kind: str, name: str) -> str:
    """Load a description from a plugin."""
    if kind == "pipe":
        from app.api.pipes import _load_pipe

        try:
            desc = _load_pipe(name).description
            if desc:
                return desc
        except Exception:
            pass

    mod = _load_plugin_module(kind, name)
    if mod:
        for attr in ("DESCRIPTION", "PIPE_DESCRIPTION"):
            val = getattr(mod, attr, None)
            if val:
                return val
        for attr in _META_ATTRS:
            meta = getattr(mod, attr, None)
            if isinstance(meta, dict) and meta.get("description"):
                return meta["description"]
            if isinstance(meta, type) and hasattr(meta, "description"):
                return meta.description

    prefix = _prefix(kind)
    pkg_name = f"{prefix}{name}"
    try:
        from importlib.metadata import metadata

        m = metadata(pkg_name)
        return m["Summary"] or ""
    except Exception:
        return ""


@router.get("/{kind}/{name}/info")
def plugin_info(kind: str, name: str) -> dict[str, Any]:
    """Get full info for an installed plugin: description and state."""
    _validate_kind(kind)
    state = get_plugin_state(kind, name)
    # Get version from installed packages
    version = None
    prefix = _prefix(kind)
    pkg_name = f"{prefix}{name}"
    try:
        from importlib.metadata import version as get_version

        version = get_version(pkg_name)
    except Exception:
        pass

    return {
        "name": name,
        "display_name": _plugin_display_name(kind, name),
        "kind": kind,
        "version": version,
        "description": _plugin_description(kind, name),
        "enabled": state["enabled"] if state else True,
        "added_at": state["added_at"] if state else None,
        "updated_at": state["updated_at"] if state else None,
        "status_changed_at": state["status_changed_at"] if state else None,
        "synced_at": state["synced_at"] if state else None,
    }


@router.get("/{kind}")
def list_plugins(kind: str) -> list[PluginInfo]:
    _validate_kind(kind)
    return list_plugins_data(kind)


@router.post("/{kind}")
def add_plugins(kind: str, body: InstallRequest) -> InstallResponse:
    _validate_kind(kind)
    results = [
        install_plugin(name, kind, index_url=body.index_url or DEFAULT_INDEX, skip_verify=body.skip_verify)
        for name in body.names
    ]
    return InstallResponse(results=results)


@router.delete("/{kind}/{name}")
def remove_plugin(kind: str, name: str) -> RemoveResponse:
    _validate_kind(kind)
    return uninstall_plugin(name, kind)


_EXCLUSIVE_KINDS = {"theme"}


@router.post("/{kind}/{name}/enable")
def enable_plugin(kind: str, name: str) -> OkResponse:
    """Enable a plugin. For exclusive kinds (theme), disables all others."""
    _validate_kind(kind)
    from app.db import get_all_plugin_states, upsert_plugin_state

    if kind in _EXCLUSIVE_KINDS:
        for state in get_all_plugin_states(kind):
            if state["name"] != name and state["enabled"]:
                upsert_plugin_state(kind, state["name"], enabled=False)
    upsert_plugin_state(kind, name, enabled=True)
    log.info("Plugin enabled: %s %s", kind, name)
    return OkResponse(ok=True, message=f"Enabled {kind} {name}")


@router.post("/{kind}/{name}/disable")
def disable_plugin(kind: str, name: str) -> OkResponse:
    """Disable a plugin. For exclusive kinds (theme), enables the default instead."""
    _validate_kind(kind)
    from app.db import upsert_plugin_state

    if kind in _EXCLUSIVE_KINDS:
        if name == "default":
            return OkResponse(ok=True, message=f"Cannot disable the default {kind}")
        upsert_plugin_state(kind, name, enabled=False)
        upsert_plugin_state(kind, "default", enabled=True)
        return OkResponse(ok=True, message=f"Switched {kind} to default")
    upsert_plugin_state(kind, name, enabled=False)
    log.info("Plugin disabled: %s %s", kind, name)
    return OkResponse(ok=True, message=f"Disabled {kind} {name}")
