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

    global _analyses_discovered
    _source_cache.clear()
    _analyses_discovered = False

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


_EP_GROUP_OVERRIDES: dict[str, str] = {"analysis": "shenas.analyses"}


def _ep_group(kind: str) -> str:
    """Entry point group name for a plugin kind."""
    return _EP_GROUP_OVERRIDES.get(kind, f"shenas.{kind}s")


def _load_plugins(kind: str, *, base: type[T], include_internal: bool = True) -> list[type[T]]:
    """Load all plugin classes of a given kind."""
    result: list[type[T]] = []
    for ep in entry_points(group=_ep_group(kind)):
        try:
            obj = ep.load()
            if isinstance(obj, type) and issubclass(obj, base) and (include_internal or not obj.internal):
                result.append(obj)
        except Exception:
            pass
    return result


_analyses_discovered = False


def _discover_analyses() -> None:
    """Load all analysis plugins via entry points.

    Importing an analysis plugin class triggers ``__init_subclass__``
    which auto-registers its mode and operations. This function is
    idempotent -- subsequent calls are no-ops.
    """
    global _analyses_discovered
    if _analyses_discovered:
        return
    _analyses_discovered = True
    import contextlib

    for ep in entry_points(group=_ep_group("analysis")):
        with contextlib.suppress(Exception):
            ep.load()


def _load_plugin(kind: str, name: str) -> type[Plugin] | None:
    """Load a single plugin class by kind and name."""
    for ep in entry_points(group=_ep_group(kind)):
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
    cls = _load_plugin("source", name) or _load_plugin_fresh("source", name)
    if cls:
        from typing import cast

        pipe = cast("Source", cls())
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

    group = _ep_group(kind)
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
