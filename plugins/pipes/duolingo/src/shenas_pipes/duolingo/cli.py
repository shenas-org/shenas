from __future__ import annotations

import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH, connect

app = create_pipe_app("Duolingo commands.")

DISPLAY_NAME = "Duolingo"
DESCRIPTION = """Syncs daily XP, course progress, and profile data from Duolingo.

Duolingo has no official API. This pipe uses the unofficial REST API
with a JWT token extracted from your browser session. The token is
long-lived (months) and stored in the OS keyring."""


@app.command()
def auth() -> None:
    """Store a Duolingo JWT token in OS keyring."""
    from shenas_pipes.duolingo.auth import AUTH_INSTRUCTIONS, _store_jwt
    from shenas_pipes.duolingo.client import DuolingoClient

    console.print(f"\n{AUTH_INSTRUCTIONS}\n")
    jwt = typer.prompt("JWT token")

    console.print("Verifying token...", style="dim")
    try:
        client = DuolingoClient(jwt)
        try:
            user = client.get_user()
            name = user.get("username", "unknown")
        finally:
            client.close()
        _store_jwt(jwt)
        console.print(f"[green]Authenticated as {name}[/green]")
        console.print("[green]JWT saved to OS keyring[/green]")
    except Exception as exc:
        console.print(f"[red]Invalid token:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def sync(
    start_date: str = typer.Option("30 days ago", help="Initial fetch window. Use 'YYYY-MM-DD' or 'N days ago'."),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download from start_date."),
) -> None:
    """Sync Duolingo data into DuckDB."""
    from shenas_pipes.core.utils import resolve_start_date
    from shenas_pipes.duolingo.auth import build_client
    from shenas_pipes.duolingo.source import courses, daily_xp, user_profile

    client = build_client()
    resolved = resolve_start_date(start_date)

    console.print(f"Syncing Duolingo data into [bold]{DB_PATH}[/bold]...", style="dim")

    resources = [
        daily_xp(client, resolved),
        courses(client),
        user_profile(client),
    ]

    def _transform() -> None:
        from shenas_schemas.habits import ensure_schema as ensure_habits
        from shenas_schemas.outcomes import ensure_schema as ensure_outcomes

        from app.transforms import run_transforms, seed_defaults
        from shenas_pipes.core.transform import load_transform_defaults

        con = connect()
        ensure_outcomes(con)
        ensure_habits(con)
        seed_defaults("duolingo", load_transform_defaults("duolingo"))
        console.print("Transforming duolingo...", style="dim")
        count = run_transforms(con, "duolingo")
        console.print(f"[green]{count} transforms done[/green]")

    run_sync("duolingo", "duolingo", resources, full_refresh, _transform)
