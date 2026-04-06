"""Plugin loaders -- resolve plugin classes and instances from entry points."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import TYPE_CHECKING, TypeVar

from shenas_components.core import Component
from shenas_plugins.core import Plugin, StaticPlugin

if TYPE_CHECKING:
    from shenas_pipes.core.pipe import Pipe
from shenas_schemas.core.schema import Schema
from shenas_themes.core import Theme
from shenas_ui.core import UI

T = TypeVar("T", bound=Plugin)

_pipe_cache: dict[str, Pipe] = {}


def _clear_caches() -> None:
    """Clear plugin caches so newly installed/removed plugins are picked up."""
    import importlib
    import importlib.metadata
    import sys

    _pipe_cache.clear()

    # Clear the FastPath lru_cache used by importlib.metadata to discover
    # .dist-info directories -- without this, entry_points() returns stale data.
    fast_path = getattr(importlib.metadata, "FastPath", None)
    if fast_path and hasattr(fast_path.__new__, "cache_clear"):
        fast_path.__new__.cache_clear()

    # Remove cached directory listings for site-packages so PathFinder rescans.
    stale = [p for p in sys.path_importer_cache if "site-packages" in p]
    for p in stale:
        del sys.path_importer_cache[p]

    importlib.invalidate_caches()


def _group(kind: str) -> str:
    """Entry point group for a plugin kind. Convention: shenas.{kind}s, except ui."""
    return "shenas.ui" if kind == "ui" else f"shenas.{kind}s"


def _load_plugins(kind: str, *, base: type[T], include_internal: bool = True) -> list[type[T]]:
    """Load all plugin classes of a given kind."""
    result: list[type[T]] = []
    for ep in entry_points(group=_group(kind)):
        try:
            obj = ep.load()
            if isinstance(obj, type) and issubclass(obj, base) and (include_internal or not obj.internal):
                result.append(obj)
        except Exception:
            pass
    return result


def _load_plugin(kind: str, name: str) -> type[Plugin] | None:
    """Load a single plugin class by kind and name."""
    for ep in entry_points(group=_group(kind)):
        if ep.name == name:
            try:
                obj = ep.load()
                if isinstance(obj, type) and issubclass(obj, Plugin):
                    return obj
            except Exception:
                pass
            break
    return None


def _load_pipe(name: str) -> Pipe:
    """Load and cache a Pipe instance by name."""
    if name in _pipe_cache:
        return _pipe_cache[name]
    for ep in entry_points(group="shenas.pipes"):
        if ep.name == name:
            cls = ep.load()
            pipe = cls()
            _pipe_cache[name] = pipe
            return pipe
    # Fallback: scan dist-info on disk (entry_points cache may be stale)
    fresh_cls = _load_plugin_fresh("pipe", name)
    if fresh_cls:
        from shenas_pipes.core.pipe import Pipe as PipeCls

        inst = fresh_cls()
        if isinstance(inst, PipeCls):
            _pipe_cache[name] = inst
            return inst
    msg = f"Pipe not found: {name}"
    raise ValueError(msg)


def _load_plugin_fresh(kind: str, name: str) -> type[Plugin] | None:
    """Load a plugin by scanning dist-info on disk (bypasses all metadata caches)."""
    import importlib
    import sys
    from importlib.metadata import PathDistribution
    from pathlib import Path

    group = _group(kind)
    for path_str in sys.path:
        if "site-packages" not in path_str:
            continue
        site = Path(path_str)
        if not site.is_dir():
            continue
        for dist_info in site.glob("*.dist-info"):
            dist = PathDistribution(dist_info)
            for ep in dist.entry_points:
                if ep.group == group and ep.name == name:
                    try:
                        mod_name, attr = ep.value.rsplit(":", 1)
                        mod = importlib.import_module(mod_name)
                        obj = getattr(mod, attr)
                        if isinstance(obj, type) and issubclass(obj, Plugin):
                            return obj
                    except Exception:
                        pass
    return None


def _load_themes(*, include_internal: bool = True) -> list[type[Theme]]:
    return _load_plugins("theme", base=Theme, include_internal=include_internal)


def _load_components(*, include_internal: bool = True) -> list[type[Component]]:
    return _load_plugins("component", base=Component, include_internal=include_internal)


def _load_uis(*, include_internal: bool = True) -> list[type[UI]]:
    return _load_plugins("ui", base=UI, include_internal=include_internal)


def _load_schemas() -> list[type[Schema]]:
    return [s for s in _load_plugins("schema", base=Schema) if s.name != "core"]


def _load_static_plugins(kind: str, *, include_internal: bool = True) -> list[type[StaticPlugin]]:
    return _load_plugins(kind, base=StaticPlugin, include_internal=include_internal)
