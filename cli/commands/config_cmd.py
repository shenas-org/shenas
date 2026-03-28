import typer
from rich.console import Console
from rich.table import Table

from cli.db import connect

console = Console()

app = typer.Typer(help="Configuration management.", invoke_without_command=True)

# Registry of known config classes — pipes register via entry points,
# but for the CLI we discover them here.
_CONFIG_CLASSES: dict[str, type] = {}


def _discover_config_classes() -> dict[str, type]:
    """Discover config classes from installed pipes."""
    if _CONFIG_CLASSES:
        return _CONFIG_CLASSES

    # Try importing config from each known pipe
    for module_path, name in [
        ("shenas_pipes.garmin.config", "GarminConfig"),
        ("shenas_pipes.lunchmoney.config", "LunchMoneyConfig"),
        ("shenas_pipes.obsidian.config", "ObsidianConfig"),
        ("shenas_pipes.gmail.config", "GmailConfig"),
    ]:
        try:
            import importlib

            mod = importlib.import_module(module_path)
            cls = getattr(mod, name)
            _CONFIG_CLASSES[cls.__table__] = cls
        except (ImportError, AttributeError):
            pass

    return _CONFIG_CLASSES


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        list_cmd()


@app.command("list")
def list_cmd(
    package: str = typer.Argument(None, help="Config table name (e.g. 'pipe_garmin')"),
) -> None:
    """List config entries. Secrets are masked."""
    from shenas_pipes.core.config import config_metadata, get_config

    con = connect()
    classes = _discover_config_classes()

    if package:
        if package not in classes:
            console.print(f"[red]Unknown config: {package}[/red]")
            console.print(f"Available: {', '.join(sorted(classes.keys()))}")
            raise typer.Exit(code=1)
        classes = {package: classes[package]}

    for table_name, cls in sorted(classes.items()):
        row = get_config(con, cls)
        meta = config_metadata(cls)

        table = Table(title=f"[bold]{table_name}[/bold]", show_lines=False)
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


@app.command("set")
def set_cmd(
    package: str = typer.Argument(help="Config table name (e.g. 'pipe_lunchmoney')"),
    key: str = typer.Argument(help="Config key (e.g. 'api_key')"),
    value: str = typer.Argument(help="Config value"),
) -> None:
    """Set a config value."""
    from shenas_pipes.core.config import set_config

    classes = _discover_config_classes()
    if package not in classes:
        console.print(f"[red]Unknown config: {package}[/red]")
        raise typer.Exit(code=1)

    con = connect()
    set_config(con, classes[package], **{key: value})
    console.print(f"[green]Set {package}.{key}[/green]")


@app.command("get")
def get_cmd(
    package: str = typer.Argument(help="Config table name"),
    key: str = typer.Argument(help="Config key"),
) -> None:
    """Get a config value."""
    from shenas_pipes.core.config import get_config_value

    classes = _discover_config_classes()
    if package not in classes:
        console.print(f"[red]Unknown config: {package}[/red]")
        raise typer.Exit(code=1)

    con = connect()
    val = get_config_value(con, classes[package], key)
    if val is None:
        console.print(f"[dim]Not set: {package}.{key}[/dim]")
        raise typer.Exit(code=1)
    console.print(val)
