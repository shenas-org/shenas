import json
from pathlib import Path

import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync

app = create_pipe_app("Obsidian daily notes commands.")

CONFIG_PATH = Path(".shenas") / "obsidian.json"


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


@app.command("config-daily-notes-folder")
def config_daily_notes_folder(
    folder: str = typer.Argument(help="Path to Obsidian daily notes folder"),
) -> None:
    """Set the path to your Obsidian daily notes folder."""
    path = Path(folder).expanduser().resolve()
    if not path.is_dir():
        console.print(f"[red]Directory not found: {path}[/red]")
        raise typer.Exit(code=1)

    md_count = len(list(path.glob("*.md")))
    config = _load_config()
    config["daily_notes_folder"] = str(path)
    _save_config(config)
    console.print(f"[green]Daily notes folder set to {path} ({md_count} .md files found)[/green]")


@app.command()
def sync(
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-sync."),
) -> None:
    """Sync Obsidian daily notes frontmatter into DuckDB."""
    from shenas_pipes.obsidian.source import daily_notes

    config = _load_config()
    notes_folder = config.get("daily_notes_folder")
    if not notes_folder:
        console.print("[red]Daily notes folder not configured.[/red]")
        console.print("Run: [bold]shenas pipe obsidian config-daily-notes-folder /path/to/daily/notes[/bold]")
        raise typer.Exit(code=1)

    if not Path(notes_folder).is_dir():
        console.print(f"[red]Directory not found: {notes_folder}[/red]")
        raise typer.Exit(code=1)

    console.print(f"Syncing daily notes from [bold]{notes_folder}[/bold]...", style="dim")

    def _transform() -> None:
        from shenas_pipes.core.db import connect
        from shenas_pipes.obsidian.transform import ObsidianMetricProvider
        from shenas_schemas.outcomes import ensure_schema

        con = connect()
        ensure_schema(con)
        provider = ObsidianMetricProvider()
        console.print("Transforming obsidian...", style="dim")
        provider.transform(con)
        console.print("[green]done[/green]")

    run_sync("obsidian", "obsidian", [daily_notes(notes_folder)], full_refresh, _transform)
