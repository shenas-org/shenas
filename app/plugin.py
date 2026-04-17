"""Base Plugin ABC and PluginInstance."""

from __future__ import annotations

import abc
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from importlib.metadata import entry_points
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, ClassVar
from urllib.request import urlopen

if TYPE_CHECKING:
    from typing import Self

from app.schema import PLUGINS
from app.table import Field, Table


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class PluginInstance(Table):
    """Per-(kind, name) install / enable / sync state for a plugin.

    The row is the deployment-time state of a plugin: when it was added,
    whether it's enabled, when it was last synced. It is a sibling of
    :class:`Plugin`, not its base -- the plugin class is a behavior
    discovered via entry points; the record is a fact about this device's
    plugin install. Decoupling the two lets ``PluginInstance`` use the
    generic :class:`Table` CRUD primitives directly while keeping
    :class:`Plugin` free of dataclass / row-shape concerns.
    """

    class _Meta:
        name = "installed"
        display_name = "Installed Plugins"
        description = "Per-plugin install / enable / sync state."
        schema = PLUGINS
        pk = ("kind", "name")
        database = "system"

    kind: Annotated[str, Field(db_type="VARCHAR", description="Plugin kind")] = ""
    name: Annotated[str, Field(db_type="VARCHAR", description="Plugin name")] = ""
    enabled: Annotated[bool, Field(db_type="BOOLEAN", description="Is enabled", db_default="TRUE")] = True
    added_at: Annotated[str, Field(db_type="TIMESTAMP", description="When added", db_default="current_timestamp")] | None = (
        None
    )
    updated_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last updated")] | None = None
    status_changed_at: Annotated[str, Field(db_type="TIMESTAMP", description="When status changed")] | None = None
    synced_at: Annotated[str, Field(db_type="TIMESTAMP", description="When last synced")] | None = None
    is_suggested: (
        Annotated[bool, Field(db_type="BOOLEAN", description="LLM-suggested, not yet accepted", db_default="FALSE")] | None
    ) = None
    metadata_json: (
        Annotated[
            str,
            Field(db_type="TEXT", description="Kind-specific metadata for data-defined plugins (JSON)", db_default="''"),
        ]
        | None
    ) = None

    @property
    def metadata(self) -> dict[str, Any]:
        """Parse ``metadata_json`` into a dict. Returns empty dict if absent."""
        import json

        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    @classmethod
    def suggested(cls, kind: str | None = None) -> list[PluginInstance]:
        """List suggested (not yet accepted) plugin instances."""
        if kind:
            return cls.all(where="is_suggested = TRUE AND kind = ?", params=[kind], order_by="added_at DESC")
        return cls.all(where="is_suggested = TRUE", order_by="added_at DESC")

    def set_enabled(self, enabled: bool) -> None:
        """Toggle enabled and bump timestamps."""
        now = _now_iso()
        if enabled != self.enabled:
            self.enabled = enabled
            self.status_changed_at = now
        self.updated_at = now
        self.save()

    @property
    def _is_single_active(self) -> bool:
        """Check if this kind uses single-active selection (only one enabled at a time)."""
        cls = Plugin.load_by_name_and_kind(self.name, self.kind)
        return getattr(cls, "single_active", False) if cls else False

    def enable(self) -> str:
        """Enable this plugin. For single-active kinds, disables all others first."""
        if self._is_single_active:
            now = _now_iso()
            for other in PluginInstance.all(
                where="kind = ? AND name != ? AND enabled = TRUE",
                params=[self.kind, self.name],
            ):
                other.enabled = False
                other.status_changed_at = now
                other.updated_at = now
                other.save()
        self.set_enabled(True)
        label = "Selected" if self._is_single_active else "Enabled"
        return f"{label} {self.kind} {self.name}"

    def disable(self) -> str:
        """Disable this plugin. For single-active kinds, re-enables the default."""
        if self._is_single_active:
            if self.name == "default":
                msg = f"Cannot deselect the default {self.kind}"
                raise ValueError(msg)
            self.set_enabled(False)
            now = _now_iso()
            default = PluginInstance.find(self.kind, "default")
            if default is not None:
                default.enabled = True
                default.status_changed_at = now
                default.updated_at = now
                default.save()
            else:
                PluginInstance(kind=self.kind, name="default", enabled=True, status_changed_at=now).insert()
            return f"Switched {self.kind} to default"
        self.set_enabled(False)
        return f"Disabled {self.kind} {self.name}"

    def mark_synced(self) -> None:
        """Stamp synced_at and updated_at."""
        now = _now_iso()
        self.synced_at = now
        self.updated_at = now
        self.save()

    @classmethod
    def get_or_create(cls, kind: str, name: str, *, enabled: bool = True) -> PluginInstance:
        """Find or create the row for (kind, name)."""
        existing = cls.find(kind, name)
        if existing is not None:
            return existing
        return PluginInstance(kind=kind, name=name, enabled=enabled, status_changed_at=_now_iso()).insert()


log = logging.getLogger("shenas.plugins")

DEFAULT_INDEX = os.environ.get("SHENAS_PACKAGE_INDEX", "https://repo.shenas.net")
PACKAGES_DIR = Path("packages")
PUBLIC_KEY_PATH = Path(".shenas") / "shenas.pub"
VALID_KINDS = frozenset({"source", "dataset", "dashboard", "frontend", "theme", "model", "transformer", "analysis"})
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
    """Base for all plugin kinds.

    A plugin's *behavior* lives on this class (entry-point discovery,
    config / auth / data accessors, ``commands``, ``version``). Its
    *deployment state* lives in :class:`PluginInstance`, a sibling row
    class. The two are joined at runtime by the (kind, name) pair.
    """

    name: ClassVar[str]
    display_name: ClassVar[str]
    display_name_plural: ClassVar[str | None] = None
    description: ClassVar[str] = ""
    internal: ClassVar[bool] = False
    enabled_by_default: ClassVar[bool] = True
    single_active: ClassVar[bool] = False

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

    @property
    def has_entities(self) -> bool:
        """True if this plugin declares an ``entity_projection`` on any of its tables."""
        try:
            import importlib

            tables_mod = importlib.import_module(f"shenas_sources.{self.name}.tables")
            return any(
                isinstance(t, type) and getattr(t, "entity_type", None) and getattr(t, "entity_projection", None)
                for t in getattr(tables_mod, "TABLES", ())
            )
        except Exception:
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

    # -- Instance lookup (get-or-create) --

    def instance(self) -> PluginInstance | None:
        """The :class:`PluginInstance` row for this (kind, name), or None."""
        return PluginInstance.find(self._kind, self.name)

    def get_or_create_instance(self) -> PluginInstance:
        """Get or create the :class:`PluginInstance` row. Use for mutations."""
        return PluginInstance.get_or_create(self._kind, self.name, enabled=self.enabled_by_default)

    @property
    def icon_path(self) -> Path | None:
        """Absolute path to the plugin's icon.svg, or None if not found."""
        import inspect

        try:
            mod_file = Path(inspect.getfile(type(self)))
            for parent in mod_file.parents:
                candidate = parent / "icon.svg"
                if candidate.exists():
                    return candidate
                if (parent / "pyproject.toml").exists():
                    break
        except Exception:
            pass
        return None

    @property
    def icon_url(self) -> str | None:
        """URL for the plugin's brand icon, or None if no icon exists."""
        if self.icon_path:
            return f"/api/plugins/{self._kind}s/{self.name}/icon.svg"
        return None

    def get_info(self) -> dict[str, Any]:
        s = self.instance()
        return {
            "name": self.name,
            "display_name": self.display_name,
            "kind": self._kind,
            "version": self.version,
            "description": self.description,
            "icon_url": self.icon_url,
            "has_config": self.has_config,
            "has_data": self.has_data,
            "has_auth": self.has_auth,
            "has_entities": self.has_entities,
            "enabled": s.enabled if s else self.enabled_by_default,
            "added_at": str(s.added_at) if s and s.added_at else None,
            "updated_at": str(s.updated_at) if s and s.updated_at else None,
            "status_changed_at": str(s.status_changed_at) if s and s.status_changed_at else None,
            "synced_at": str(s.synced_at) if s and s.synced_at else None,
        }

    # -- Entry-point discovery (classmethods) --

    _EP_GROUP_OVERRIDES: ClassVar[dict[str, str]] = {"analysis": "shenas.analyses"}
    _cache_clear_hooks: ClassVar[list[Any]] = []

    @classmethod
    def _ep_group(cls, kind: str) -> str:
        """Entry point group name for a plugin kind."""
        return cls._EP_GROUP_OVERRIDES.get(kind, f"shenas.{kind}s")

    @classmethod
    def load_by_kind(cls, kind: str, *, include_internal: bool = True) -> list[type[Plugin]]:
        """Load all plugin classes of a given kind via entry points."""

        result: list[type[Plugin]] = []
        for ep in entry_points(group=cls._ep_group(kind)):
            try:
                obj = ep.load()
                if isinstance(obj, type) and issubclass(obj, Plugin) and (include_internal or not obj.internal):
                    result.append(obj)
            except Exception:
                pass
        return result

    @classmethod
    def load_by_name_and_kind(cls, name: str, kind: str) -> type[Plugin] | None:
        """Load a single plugin class by kind and name.

        Normalizes hyphens and underscores so both ``claude-code`` and
        ``claude_code`` resolve to the same entry point.
        """
        normalized = name.replace("-", "_")
        for ep in entry_points(group=cls._ep_group(kind)):
            if ep.name.replace("-", "_") == normalized:
                try:
                    obj = ep.load()
                    if isinstance(obj, type) and issubclass(obj, Plugin):
                        return obj
                except Exception:
                    pass
                break
        return None

    @classmethod
    def _load_fresh(cls, kind: str, name: str) -> type[Plugin] | None:
        """Load a plugin by scanning dist-info on disk (bypasses all metadata caches)."""
        import importlib
        from importlib.metadata import PathDistribution

        group = cls._ep_group(kind)
        for path_str in sys.path:
            if "site-packages" not in path_str:
                continue
            site = Path(path_str)
            if not site.is_dir():
                continue
            for dist_info in site.glob("*.dist-info"):
                dist = PathDistribution(dist_info)
                for ep in dist.entry_points:
                    if ep.group == group and ep.name.replace("-", "_") == name.replace("-", "_"):
                        try:
                            mod_name, attr = ep.value.rsplit(":", 1)
                            mod = importlib.import_module(mod_name)
                            obj = getattr(mod, attr)
                            if isinstance(obj, type) and issubclass(obj, Plugin):
                                return obj
                        except Exception:
                            pass
        return None

    @classmethod
    def clear_caches(cls) -> None:
        """Clear plugin discovery caches so newly installed/removed plugins are picked up."""
        import importlib
        import importlib.metadata

        fast_path = getattr(importlib.metadata, "FastPath", None)
        if fast_path and hasattr(fast_path.__new__, "cache_clear"):
            fast_path.__new__.cache_clear()

        stale = [p for p in sys.path_importer_cache if "site-packages" in p]
        for p in stale:
            del sys.path_importer_cache[p]

        importlib.invalidate_caches()

        for hook in cls._cache_clear_hooks:
            hook()

    @classmethod
    def load_all(cls, *, include_internal: bool = True) -> list[type[Self]]:
        """Load all plugin classes of this kind. Call on a subclass, e.g. ``Source.load_all()``."""
        return cls.load_by_kind(cls._kind, include_internal=include_internal)  # ty: ignore[invalid-return-type, invalid-argument-type]

    @classmethod
    def load_by_name(cls, name: str) -> type[Self] | None:
        """Load a single plugin class by name within this kind. Call on a subclass."""
        return cls.load_by_name_and_kind(name, cls._kind) or cls._load_fresh(cls._kind, name)  # ty: ignore[invalid-return-type, invalid-argument-type]

    # -- Package management (classmethods) --

    @staticmethod
    def list_installed(kind: str) -> list[dict[str, Any]]:
        """List installed plugins of a given kind with full info."""
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
            plugin_cls = Plugin.load_by_name_and_kind(short_name, kind) or Plugin._load_fresh(kind, short_name)
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
                    "name": pi.get("name", short_name),
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
        pkg = Plugin.pkg(kind, name)
        cls = Plugin.load_by_name_and_kind(name, kind)
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
            Plugin.clear_caches()
            Plugin.load_by_name_and_kind(name, kind) or Plugin._load_fresh(kind, name)
            PluginInstance.get_or_create(kind, name, enabled=True)
            display = name.replace("-", " ").title()
            return True, f"Added {display} {kind.title()}"
        return False, result.stderr.strip() or f"Failed to add {pkg}"

    @staticmethod
    def uninstall(kind: str, name: str) -> tuple[bool, str]:
        """Uninstall a plugin. Returns (ok, message)."""
        pkg = Plugin.pkg(kind, name)
        cls = Plugin.load_by_name_and_kind(name, kind)
        if (cls and cls.internal) or name == "core":
            return False, f"{pkg} is an internal plugin"

        record = PluginInstance.find(kind, name)
        if record:
            record.delete()
        result = subprocess.run(
            ["uv", "pip", "uninstall", pkg, "--python", _python_executable()],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            Plugin.clear_caches()
            display = name.replace("-", " ").title()
            return True, f"Removed {display} {kind.title()}"
        return False, result.stderr.strip() or f"Failed to uninstall {pkg}"
