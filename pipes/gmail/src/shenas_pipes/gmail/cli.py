from __future__ import annotations

import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync

app = create_pipe_app("Gmail commands.")

DISPLAY_NAME = "Gmail"
DESCRIPTION = """Syncs email metadata from Gmail.

Uses Google OAuth2 with shared credentials from shenas-pipe-core.
Authorization URL is passed back to the CLI for browser-based consent."""


@app.command()
def auth() -> None:
    """Authenticate with Gmail via OAuth2. Opens browser for Google login."""
    from shenas_pipes.gmail.auth import build_client

    console.print("Opening browser for Google authentication...", style="dim")
    try:
        service = build_client(run_auth_flow=True)
        profile = service.users().getProfile(userId="me").execute()
        console.print(f"[green]Authenticated as {profile['emailAddress']}[/green]")
        console.print("[green]Token saved to OS keyring[/green]")
    except Exception as exc:
        console.print(f"[red]Authentication failed:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def sync(
    query: str = typer.Option("", "--query", "-q", help="Gmail search query (e.g. 'after:2026/01/01')"),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download."),
) -> None:
    """Sync Gmail messages into DuckDB."""
    from shenas_pipes.gmail.auth import build_client
    from shenas_pipes.gmail.source import labels, messages

    service = build_client()
    console.print("Syncing Gmail data...", style="dim")

    run_sync("gmail", "gmail", [messages(service, query), labels(service)], full_refresh)
