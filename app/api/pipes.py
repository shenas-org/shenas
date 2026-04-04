"""Shared pipe loader -- resolves Pipe instances from entry points."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from shenas_pipes.core.abc import Pipe

_pipe_cache: dict[str, Pipe] = {}


def _load_pipe(name: str) -> Pipe:
    """Load and cache a Pipe instance by entry-point name."""
    if name in _pipe_cache:
        return _pipe_cache[name]
    for ep in entry_points(group="shenas.pipes"):
        if ep.name == name:
            cls = ep.load()
            pipe = cls()
            _pipe_cache[name] = pipe
            return pipe
    raise HTTPException(status_code=404, detail=f"Pipe not found: {name}")
