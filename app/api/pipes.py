"""Pipe discovery API -- lists installed pipes and their commands."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys

from fastapi import APIRouter

from app.cli.commands.pkg import check_signature

router = APIRouter(prefix="/pipes", tags=["pipes"])

PIPE_PREFIX = "shenas-pipe-"

SYNC_OPTIONS = [
    {"name": "start_date", "default": "30 days ago", "help": "Start date (YYYY-MM-DD or 'N days ago')"},
    {"name": "full_refresh", "default": False, "help": "Drop and re-download all data"},
]


def _pipe_commands(name: str) -> list[dict[str, object]]:
    """Detect available commands for a pipe by inspecting its modules."""
    commands: list[dict[str, object]] = [{"name": "sync", "options": SYNC_OPTIONS}]

    # Check if pipe has auth (AUTH_FIELDS in auth module)
    try:
        importlib.invalidate_caches()
        for key in list(sys.modules):
            if key.startswith(f"shenas_pipes.{name}"):
                del sys.modules[key]
        auth_mod = importlib.import_module(f"shenas_pipes.{name}.auth")
        fields = getattr(auth_mod, "AUTH_FIELDS", None)
        if fields is not None:
            commands.append({"name": "auth", "options": []})
    except (ImportError, ModuleNotFoundError):
        pass

    # Check if pipe has config (a config module with a dataclass)
    try:
        config_mod = importlib.import_module(f"shenas_pipes.{name}.config")
        # Any class with __table__ is a config class
        for attr_name in dir(config_mod):
            cls = getattr(config_mod, attr_name)
            if hasattr(cls, "__table__") and isinstance(cls.__table__, str):
                commands.append({"name": "config", "options": []})
                break
    except (ImportError, ModuleNotFoundError):
        pass

    return commands


@router.get("")
def list_pipes() -> list[dict[str, object]]:
    """List installed pipes with their available commands."""
    result = subprocess.run(
        ["uv", "pip", "list", "--format", "json", "--python", sys.executable], capture_output=True, text=True
    )
    if result.returncode != 0:
        return []

    packages = json.loads(result.stdout)
    pipes = []
    for p in sorted(packages, key=lambda x: x["name"]):
        if p["name"].startswith(PIPE_PREFIX) and not p["name"].endswith("-core"):
            name = p["name"].removeprefix(PIPE_PREFIX)
            sig = check_signature(p["name"], p["version"])
            commands = _pipe_commands(name)
            pipes.append({"name": name, "version": p["version"], "signature": sig, "commands": commands})
    return pipes
