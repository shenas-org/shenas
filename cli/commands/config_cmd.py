import importlib

import typer
from rich.console import Console
from rich.table import Table

from cli.db import connect

console = Console()

app = typer.Typer(help="Configuration management.", invoke_without_command=True)

TYPES = ("pipe", "schema", "component")

_CONFIG_CLASSES: dict[str, type] = {}


def _discover_config_classes() -> dict[str, type]:
    """Discover config classes from installed packages."""
    if _CONFIG_CLASSES:
        return _CONFIG_CLASSES

    for module_path, class_name in [
        ("shenas_pipes.garmin.config", "GarminConfig"),
        ("shenas_pipes.lunchmoney.config", "LunchMoneyConfig"),
        ("shenas_pipes.obsidian.config", "ObsidianConfig"),
        ("shenas_pipes.gmail.config", "GmailConfig"),
    ]:
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            _CONFIG_CLASSES[cls.__table__] = cls
        except (ImportError, AttributeError):
            pass

    return _CONFIG_CLASSES


def _resolve_table(kind: str | None, name: str | None) -> str | None:
    """Resolve 'pipe garmin' -> 'pipe_garmin', or None for all."""
    if kind and name:
        return f"{kind}_{name}"
    return None


def _show_config(table_filter: str | None) -> None:
    """Show config entries, optionally filtered by table name."""
    from shenas_pipes.core.config import config_metadata, get_config

    con = connect()
    classes = _discover_config_classes()

    if table_filter:
        if table_filter not in classes:
            console.print(f"[red]Unknown config: {table_filter}[/red]")
            available = [f"{t.replace('_', ' ', 1)}" for t in sorted(classes.keys())]
            console.print(f"Available: {', '.join(available)}")
            raise typer.Exit(code=1)
        classes = {table_filter: classes[table_filter]}

    for table_name, cls in sorted(classes.items()):
        row = get_config(con, cls)
        meta = config_metadata(cls)

        display_name = table_name.replace("_", " ", 1)
        table = Table(title=f"[bold]{display_name}[/bold]", show_lines=False)
        table.add_column("Key", style="green")
        table.add_column("Value")
        table.add_column("Description", style="dim")

        for col in meta["columns"]:
            if col["name"] == "id":
                continue
            val = row.get(col["name"]) if row else None
            is_secret = col.get("category") == "secret"
            display_val = "********" if (is_secret and val) else (str(val) if val is not None else "[dim]not set[/dim]")
            table.add_row(col["name"], display_val, col.get("description", ""))

        console.print(table)
        console.print()


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        _show_config(None)
        raise typer.Exit()


@app.command("list")
def list_cmd(
    kind: str = typer.Argument(None, help="Package type: pipe, schema, or component"),
    name: str = typer.Argument(None, help="Package name (e.g. 'garmin')"),
) -> None:
    """List config entries. Secrets are masked."""
    _show_config(_resolve_table(kind, name))


@app.command("set")
def set_cmd(
    kind: str = typer.Argument(help="Package type: pipe, schema, or component"),
    name: str = typer.Argument(help="Package name (e.g. 'lunchmoney')"),
    key: str = typer.Argument(help="Config key (e.g. 'api_key')"),
    value: str = typer.Argument(help="Config value"),
) -> None:
    """Set a config value."""
    from shenas_pipes.core.config import set_config

    table_name = _resolve_table(kind, name)
    classes = _discover_config_classes()
    if table_name not in classes:
        console.print(f"[red]Unknown config: {kind} {name}[/red]")
        raise typer.Exit(code=1)

    con = connect()
    set_config(con, classes[table_name], **{key: value})
    console.print(f"[green]Set {kind} {name}.{key}[/green]")


@app.command("get")
def get_cmd(
    kind: str = typer.Argument(help="Package type: pipe, schema, or component"),
    name: str = typer.Argument(help="Package name"),
    key: str = typer.Argument(help="Config key"),
) -> None:
    """Get a config value."""
    from shenas_pipes.core.config import get_config_value

    table_name = _resolve_table(kind, name)
    classes = _discover_config_classes()
    if table_name not in classes:
        console.print(f"[red]Unknown config: {kind} {name}[/red]")
        raise typer.Exit(code=1)

    con = connect()
    val = get_config_value(con, classes[table_name], key)
    if val is None:
        console.print(f"[dim]Not set: {kind} {name}.{key}[/dim]")
        raise typer.Exit(code=1)
    console.print(val)


@app.command("delete")
def delete_cmd(
    kind: str = typer.Argument(help="Package type: pipe, schema, or component"),
    name: str = typer.Argument(help="Package name"),
    key: str = typer.Argument(None, help="Config key (omit to delete all)"),
) -> None:
    """Delete a config entry or all config for a package."""
    from shenas_pipes.core.config import delete_config, set_config

    table_name = _resolve_table(kind, name)
    classes = _discover_config_classes()
    if table_name not in classes:
        console.print(f"[red]Unknown config: {kind} {name}[/red]")
        raise typer.Exit(code=1)

    con = connect()
    if key:
        set_config(con, classes[table_name], **{key: None})
        console.print(f"[green]Cleared {kind} {name}.{key}[/green]")
    else:
        delete_config(con, classes[table_name])
        console.print(f"[green]Deleted all config for {kind} {name}[/green]")
