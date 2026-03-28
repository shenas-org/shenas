"""Pipe discovery API -- lists installed pipes and their commands."""

import inspect
from importlib.metadata import entry_points

import typer
from fastapi import APIRouter

router = APIRouter(prefix="/pipes", tags=["pipes"])


@router.get("")
def list_pipes() -> list[dict]:
    """List installed pipes with their available commands and options."""
    pipes = []
    for ep in sorted(entry_points(group="shenas.pipes"), key=lambda e: e.name):
        if ep.name == "core":
            continue
        try:
            pipe_app = ep.load()
            commands = []
            for cmd in pipe_app.registered_commands:
                cmd_name = cmd.name or (getattr(cmd.callback, "__name__", None) if cmd.callback else None)
                if not cmd_name or not cmd.callback:
                    continue
                options = []
                for p_name, p in inspect.signature(cmd.callback).parameters.items():
                    if isinstance(p.default, typer.models.OptionInfo):
                        options.append(
                            {
                                "name": p_name,
                                "default": p.default.default,
                                "help": p.default.help,
                            }
                        )
                commands.append({"name": cmd_name, "options": options})
            pipes.append({"name": ep.name, "commands": commands})
        except Exception:
            pipes.append({"name": ep.name, "commands": []})
    return pipes
