"""Plugin loaders -- resolve plugin classes and instances from entry points."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import TypeVar

from shenas_pipes.core.abc import UI, Component, Pipe, Plugin, Schema, StaticPlugin, Theme

T = TypeVar("T", bound=Plugin)

_pipe_cache: dict[str, Pipe] = {}


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
    msg = f"Pipe not found: {name}"
    raise ValueError(msg)


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
