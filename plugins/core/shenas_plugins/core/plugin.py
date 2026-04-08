"""Base Plugin ABC and _SelectOneMixin."""

from __future__ import annotations

import abc
import json
import logging
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Annotated, Any, ClassVar
from urllib.request import urlopen

from shenas_plugins.core.table import Field, Table

log = logging.getLogger("shenas.plugins")

DEFAULT_INDEX = "https://repo.shenas.net"
PACKAGES_DIR = Path("packages")
PUBLIC_KEY_PATH = Path(".shenas") / "shenas.pub"
VALID_KINDS = frozenset({"source", "dataset", "dashboard", "frontend", "theme", "model"})
_PLUGIN_VENV = Path.home() / ".shenas" / "plugins"


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


def _is_frozen() -> bool:
    return getattr(sys, "_MEIPASS", None) is not None


def _ensure_plugin_venv() -> Path:
    python = _PLUGIN_VENV / "bin" / "python3"
    if not python.exists():
        log.info("Creating plugin venv at %s", _PLUGIN_VENV)
        subprocess.run(["uv", "venv", str(_PLUGIN_VENV), "--python", "3.11"], check=True)
    return python


def _python_executable() -> str:
    if _is_frozen():
        return str(_ensure_plugin_venv())
    venv = sys.prefix
    if venv != sys.base_prefix:
        venv_python = Path(venv) / "bin" / "python3"
        if venv_python.exists():
            return str(venv_python)
    return sys.executable


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


def _load_public_key(path: Path) -> Any:
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    key = load_pem_public_key(path.read_bytes())
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if not isinstance(key, Ed25519PublicKey):
        msg = f"Expected Ed25519 public key, got {type(key)}"
        raise TypeError(msg)
    return key


def _verify_bytes(public_key: Any, data: bytes, sig_b64: str) -> bool:
    import base64

    try:
        public_key.verify(base64.b64decode(sig_b64), data)
        return True
    except Exception:
        return False


def _verify_file(public_key: Any, file_path: Path, sig_b64: str) -> bool:
    return _verify_bytes(public_key, file_path.read_bytes(), sig_b64)


def _check_signature(pkg: str, version: str) -> str:
    if not PUBLIC_KEY_PATH.exists():
        return "no key"
    normalized = pkg.replace("-", "_")
    matches = list(PACKAGES_DIR.glob(f"{normalized}-{version}*.whl")) if PACKAGES_DIR.is_dir() else []
    if not matches:
        return "unsigned"
    wheel_path = matches[0]
    sig_path = wheel_path.with_suffix(wheel_path.suffix + ".sig")
    if not sig_path.exists():
        return "unsigned"
    pub_key = _load_public_key(PUBLIC_KEY_PATH)
    return "valid" if _verify_file(pub_key, wheel_path, sig_path.read_text().strip()) else "invalid"


def _verify_from_index(pkg: str, index_url: str, pub_key: Any) -> str | None:
    normalized = pkg.replace("_", "-").lower()
    try:
        with urlopen(f"{index_url}/simple/{normalized}/") as resp:
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
        return f"No wheel found for {pkg} in repository"

    wheel_url = f"{index_url}{wheel_href}" if wheel_href.startswith("/") else f"{index_url}/{wheel_href}"
    try:
        with urlopen(f"{wheel_url}.sig") as resp:
            sig_b64 = resp.read().decode().strip()
    except Exception:
        return f"No signature found for {pkg}"
    try:
        with urlopen(wheel_url) as resp:
            wheel_bytes = resp.read()
    except Exception as exc:
        return f"Cannot download wheel: {exc}"

    if not _verify_bytes(pub_key, wheel_bytes, sig_b64):
        return f"SIGNATURE VERIFICATION FAILED for {pkg}"
    return None


# ---------------------------------------------------------------------------
# Plugin ABC
# ---------------------------------------------------------------------------


class Plugin(abc.ABC):
    """Base for all plugin kinds."""

    class _Table(Table):
        table_name: ClassVar[str] = "plugins"
        table_schema: ClassVar[str | None] = "shenas_system"
        table_display_name: ClassVar[str] = "Installed Plugins"
        table_description: ClassVar[str | None] = "Per-plugin install / enable / sync state."
        table_pk: ClassVar[tuple[str, ...]] = ("kind", "name", "user_id")

        kind: Annotated[str, Field(db_type="VARCHAR", description="Plugin kind")] = ""
        name: Annotated[str, Field(db_type="VARCHAR", description="Plugin name")] = ""
        user_id: Annotated[int, Field(db_type="INTEGER", description="User ID (0 = single-user)")] = 0
        enabled: Annotated[bool, Field(db_type="BOOLEAN", description="Is enabled", db_default="TRUE")] = True
        added_at: (
            Annotated[str, Field(db_type="TIMESTAMP", description="When added", db_default="current_timestamp")] | None
        ) = None
        updated_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last updated")] | None = None
        status_changed_at: Annotated[str, Field(db_type="TIMESTAMP", description="When status changed")] | None = None
        synced_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last synced")] | None = None

    name: ClassVar[str]
    display_name: ClassVar[str]
    description: ClassVar[str] = ""
    internal: ClassVar[bool] = False
    enabled_by_default: ClassVar[bool] = True

    @staticmethod
    def pkg(kind: str, name: str) -> str:
        return f"shenas-{kind}-{name}"

    @property
    def package_name(self) -> str:
        return self.pkg(self._kind, self.name)

    @property
    def version(self) -> str | None:
        try:
            from importlib.metadata import version

            return version(self.package_name)
        except Exception:
            return None

    @property
    def _kind(self) -> str:
        return "plugin"

    @property
    def has_config(self) -> bool:
        return False

    @property
    def has_data(self) -> bool:
        return False

    @property
    def has_auth(self) -> bool:
        return False

    def get_config_entries(self) -> list[dict[str, str | None]]:
        return []

    def set_config_value(self, key: str, value: str | None) -> None:  # noqa: B027
        """Set a config value. Override in subclasses with config."""

    def get_config_value(self, key: str) -> Any | None:  # noqa: ARG002
        return None

    def delete_config(self) -> None:  # noqa: B027
        """Delete all config. Override in subclasses with config."""

    @property
    def commands(self) -> list[str]:
        return []

    # -- State management --

    @property
    def _user_id(self) -> int:
        from app.user_context import get_current_user_id

        return get_current_user_id()

    @property
    def state(self) -> dict[str, Any] | None:
        from app.db import cursor

        uid = self._user_id
        with cursor() as cur:
            row = cur.execute(
                "SELECT kind, name, enabled, added_at, updated_at, status_changed_at, synced_at "
                "FROM shenas_system.plugins WHERE kind = ? AND name = ? AND user_id = ?",
                [self._kind, self.name, uid],
            ).fetchone()
        if not row:
            return None
        return {
            "kind": row[0],
            "name": row[1],
            "enabled": row[2],
            "added_at": str(row[3]) if row[3] else None,
            "updated_at": str(row[4]) if row[4] else None,
            "status_changed_at": str(row[5]) if row[5] else None,
            "synced_at": str(row[6]) if row[6] else None,
        }

    @property
    def enabled(self) -> bool:
        s = self.state
        return s["enabled"] if s else self.enabled_by_default

    def save_state(self, *, enabled: bool) -> None:
        from app.db import cursor

        uid = self._user_id
        now = "current_timestamp"
        with cursor() as cur:
            row = cur.execute(
                "SELECT enabled FROM shenas_system.plugins WHERE kind = ? AND name = ? AND user_id = ?",
                [self._kind, self.name, uid],
            ).fetchone()
            if row is not None:
                if enabled != row[0]:
                    cur.execute(
                        f"UPDATE shenas_system.plugins SET enabled = ?, status_changed_at = {now}, updated_at = {now} "
                        "WHERE kind = ? AND name = ? AND user_id = ?",
                        [enabled, self._kind, self.name, uid],
                    )
                else:
                    cur.execute(
                        f"UPDATE shenas_system.plugins SET updated_at = {now} "
                        "WHERE kind = ? AND name = ? AND user_id = ?",
                        [self._kind, self.name, uid],
                    )
            else:
                cur.execute(
                    f"INSERT INTO shenas_system.plugins (kind, name, user_id, enabled, added_at, status_changed_at) "
                    f"VALUES (?, ?, ?, ?, {now}, {now})",
                    [self._kind, self.name, uid, enabled],
                )

    def remove_state(self) -> None:
        from app.db import cursor

        uid = self._user_id
        with cursor() as cur:
            cur.execute(
                "DELETE FROM shenas_system.plugins WHERE kind = ? AND name = ? AND user_id = ?",
                [self._kind, self.name, uid],
            )

    def mark_synced(self) -> None:
        from app.db import cursor

        uid = self._user_id
        with cursor() as cur:
            row = cur.execute(
                "SELECT 1 FROM shenas_system.plugins WHERE kind = ? AND name = ? AND user_id = ?",
                [self._kind, self.name, uid],
            ).fetchone()
        if not row:
            self.save_state(enabled=True)
        with cursor() as cur:
            cur.execute(
                "UPDATE shenas_system.plugins SET synced_at = current_timestamp, updated_at = current_timestamp "
                "WHERE kind = ? AND name = ? AND user_id = ?",
                [self._kind, self.name, uid],
            )

    def enable(self) -> str:
        self.save_state(enabled=True)
        return f"Enabled {self._kind} {self.name}"

    def disable(self) -> str:
        self.save_state(enabled=False)
        return f"Disabled {self._kind} {self.name}"

    def get_info(self) -> dict[str, Any]:
        s = self.state
        return {
            "name": self.name,
            "display_name": self.display_name,
            "kind": self._kind,
            "version": self.version,
            "description": self.description,
            "has_config": self.has_config,
            "has_data": self.has_data,
            "has_auth": self.has_auth,
            "enabled": s["enabled"] if s else self.enabled_by_default,
            "added_at": s["added_at"] if s else None,
            "updated_at": s["updated_at"] if s else None,
            "status_changed_at": s["status_changed_at"] if s else None,
            "synced_at": s["synced_at"] if s else None,
        }

    # -- Package management (classmethods) --

    @staticmethod
    def list_installed(kind: str) -> list[dict[str, Any]]:
        """List installed plugins of a given kind with full info."""
        from app.api.sources import _load_plugin, _load_plugin_fresh

        prefix = Plugin.pkg(kind, "")
        result = subprocess.run(
            ["uv", "pip", "list", "--format", "json", "--python", _python_executable()],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return []

        installed = json.loads(result.stdout)
        items = []
        for p in sorted(installed, key=lambda x: x["name"]):
            if not p["name"].startswith(prefix):
                continue
            short_name = p["name"].removeprefix(prefix)
            if short_name == "core":
                continue
            plugin_cls = _load_plugin(kind, short_name) or _load_plugin_fresh(kind, short_name)
            if plugin_cls and plugin_cls.internal:
                continue
            if plugin_cls:
                plugin = plugin_cls()
                pi = plugin.get_info()
                config_entries = plugin.get_config_entries() if plugin.has_config else []
            else:
                pi = {
                    "name": short_name,
                    "display_name": short_name.replace("-", " ").title(),
                    "enabled": True,
                }
                config_entries = []
            items.append(
                {
                    **pi,
                    "name": short_name,
                    "package": p["name"],
                    "version": p["version"],
                    "signature": _check_signature(p["name"], p["version"]),
                    "config_entries": config_entries,
                }
            )
        return items

    @staticmethod
    def install(
        kind: str,
        name: str,
        *,
        index_url: str = DEFAULT_INDEX,
        skip_verify: bool = False,
    ) -> tuple[bool, str]:
        """Install a plugin. Returns (ok, message)."""
        from app.api.sources import _load_plugin

        pkg = Plugin.pkg(kind, name)
        cls = _load_plugin(kind, name)
        if (cls and cls.internal) or name == "core":
            return False, f"{pkg} is an internal plugin"

        if not skip_verify:
            if not PUBLIC_KEY_PATH.exists():
                return False, f"Public key not found at {PUBLIC_KEY_PATH}"
            pub_key = _load_public_key(PUBLIC_KEY_PATH)
            error = _verify_from_index(pkg, index_url, pub_key)
            if error:
                return False, error

        result = subprocess.run(
            [
                "uv",
                "pip",
                "install",
                pkg,
                "--index-url",
                f"{index_url}/simple/",
                "--extra-index-url",
                "https://pypi.org/simple/",
                "--python",
                _python_executable(),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            from app.api.sources import _clear_caches, _load_plugin, _load_plugin_fresh

            _clear_caches()
            cls = _load_plugin(kind, name) or _load_plugin_fresh(kind, name)
            if cls:
                cls().save_state(enabled=True)
            else:
                log.warning("Could not load plugin %s/%s after install to save state", kind, name)
            display = name.replace("-", " ").title()
            return True, f"Added {display} {kind.title()}"
        return False, result.stderr.strip() or f"Failed to add {pkg}"

    @staticmethod
    def uninstall(kind: str, name: str) -> tuple[bool, str]:
        """Uninstall a plugin. Returns (ok, message)."""
        from app.api.sources import _load_plugin

        pkg = Plugin.pkg(kind, name)
        cls = _load_plugin(kind, name)
        if (cls and cls.internal) or name == "core":
            return False, f"{pkg} is an internal plugin"

        if cls:
            cls().remove_state()
        else:
            log.warning("Could not load plugin %s/%s before uninstall to remove state", kind, name)
        result = subprocess.run(
            ["uv", "pip", "uninstall", pkg, "--python", _python_executable()],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            from app.api.sources import _clear_caches

            _clear_caches()
            display = name.replace("-", " ").title()
            return True, f"Removed {display} {kind.title()}"
        return False, result.stderr.strip() or f"Failed to uninstall {pkg}"


class _SelectOneMixin:
    """Mixin for plugin kinds where only one can be active at a time."""

    enabled_by_default: ClassVar[bool] = False

    def enable(self) -> str:
        from app.db import cursor
        from app.user_context import get_current_user_id

        uid = get_current_user_id()
        with cursor() as cur:
            cur.execute(
                "UPDATE shenas_system.plugins SET enabled = false, "
                "status_changed_at = current_timestamp, updated_at = current_timestamp "
                "WHERE kind = ? AND name != ? AND user_id = ? AND enabled = true",
                [self._kind, self.name, uid],
            )
        self.save_state(enabled=True)
        return f"Selected {self._kind} {self.name}"

    def disable(self) -> str:
        if self.name == "default":
            return f"Cannot deselect the default {self._kind}"
        self.save_state(enabled=False)
        from app.db import cursor
        from app.user_context import get_current_user_id

        uid = get_current_user_id()
        now = "current_timestamp"
        with cursor() as cur:
            row = cur.execute(
                "SELECT 1 FROM shenas_system.plugins WHERE kind = ? AND name = 'default' AND user_id = ?",
                [self._kind, uid],
            ).fetchone()
            if row:
                cur.execute(
                    f"UPDATE shenas_system.plugins SET enabled = true, status_changed_at = {now}, updated_at = {now} "
                    "WHERE kind = ? AND name = 'default' AND user_id = ?",
                    [self._kind, uid],
                )
            else:
                cur.execute(
                    f"INSERT INTO shenas_system.plugins (kind, name, user_id, enabled, added_at, status_changed_at) "
                    f"VALUES (?, 'default', ?, true, {now}, {now})",
                    [self._kind, uid],
                )
        return f"Switched {self._kind} to default"
