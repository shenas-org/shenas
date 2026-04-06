"""Plugin loaders -- resolve plugin classes and instances from entry points."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import TYPE_CHECKING, TypeVar

from shenas_dashboards.core import Dashboard
from shenas_plugins.core import Plugin, StaticPlugin

if TYPE_CHECKING:
    from shenas_sources.core.source import Source
from shenas_datasets.core.dataset import Dataset
from shenas_frontends.core import Frontend
from shenas_themes.core import Theme

T = TypeVar("T", bound=Plugin)

_source_cache: dict[str, Source] = {}


def _clear_caches() -> None:
    """Clear plugin caches so newly installed/removed plugins are picked up."""
    import importlib
    import importlib.metadata
    import sys

    _source_cache.clear()

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
    return "shenas.frontends" if kind == "frontend" else f"shenas.{kind}s"


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


def _load_source(name: str) -> Source:
    """Load and cache a Source instance by name."""
    if name in _source_cache:
        return _source_cache[name]
    for ep in entry_points(group="shenas.sources"):
        if ep.name == name:
            cls = ep.load()
            pipe = cls()
            _source_cache[name] = pipe
            return pipe
    # Fallback: scan dist-info on disk (entry_points cache may be stale)
    fresh_cls = _load_plugin_fresh("source", name)
    if fresh_cls:
        from typing import cast

        pipe = cast("Source", fresh_cls())
        _source_cache[name] = pipe
        return pipe
    msg = f"Source not found: {name}"
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


def _load_dashboards(*, include_internal: bool = True) -> list[type[Dashboard]]:
    return _load_plugins("dashboard", base=Dashboard, include_internal=include_internal)


def _load_frontends(*, include_internal: bool = True) -> list[type[Frontend]]:
    return _load_plugins("frontend", base=Frontend, include_internal=include_internal)


def _load_datasets() -> list[type[Dataset]]:
    return [s for s in _load_plugins("dataset", base=Dataset) if s.name != "core"]


def _load_static_plugins(kind: str, *, include_internal: bool = True) -> list[type[StaticPlugin]]:
    return _load_plugins(kind, base=StaticPlugin, include_internal=include_internal)
