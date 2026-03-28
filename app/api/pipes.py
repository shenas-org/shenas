"""Pipe discovery API -- lists installed pipes and their commands."""

import json
import subprocess

from fastapi import APIRouter

router = APIRouter(prefix="/pipes", tags=["pipes"])

PIPE_PREFIX = "shenas-pipe-"

# Standard commands for pipes -- avoids needing to import and introspect the pipe module
# (which fails for freshly installed pipes in a running process due to metadata caching).
STANDARD_PIPE_COMMANDS = [
    {
        "name": "sync",
        "options": [
            {"name": "start_date", "default": "30 days ago", "help": "Start date (YYYY-MM-DD or 'N days ago')"},
            {"name": "full_refresh", "default": False, "help": "Drop and re-download all data"},
        ],
    },
    {"name": "auth", "options": []},
]


@router.get("")
def list_pipes() -> list[dict]:
    """List installed pipes with their available commands."""
    result = subprocess.run(["uv", "pip", "list", "--format", "json"], capture_output=True, text=True)
    if result.returncode != 0:
        return []

    packages = json.loads(result.stdout)
    pipes = []
    for p in sorted(packages, key=lambda x: x["name"]):
        if p["name"].startswith(PIPE_PREFIX) and not p["name"].endswith("-core"):
            name = p["name"].removeprefix(PIPE_PREFIX)
            pipes.append({"name": name, "version": p["version"], "commands": STANDARD_PIPE_COMMANDS})
    return pipes
