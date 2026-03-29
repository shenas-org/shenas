from __future__ import annotations

import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync
from shenas_pipes.core.db import DB_PATH, connect

app = create_pipe_app("Duolingo commands.")


@app.command()
def auth() -> None:
    """Authenticate with Duolingo and save the JWT token to OS keyring."""
    from shenas_pipes.duolingo.client import DuolingoClient
    from shenas_pipes.duolingo.auth import _store_jwt

    username = typer.prompt("Username or email")
    password = typer.prompt("Password", hide_input=True)

    console.print("Authenticating...", style="dim")
    try:
        jwt = DuolingoClient.login(username, password)
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
        console.print(f"[red]Authentication failed:[/red] {exc}")
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
        from shenas_pipes.duolingo.transform import DuolingoMetricProvider
        from shenas_schemas.habits import ensure_schema as ensure_habits
        from shenas_schemas.outcomes import ensure_schema as ensure_outcomes

        con = connect()
        ensure_outcomes(con)
        ensure_habits(con)
        provider = DuolingoMetricProvider()
        console.print("Transforming duolingo...", style="dim")
        provider.transform(con)
        console.print("[green]done[/green]")

    run_sync("duolingo", "duolingo", resources, full_refresh, _transform)
