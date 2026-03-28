from pathlib import Path

import typer

from shenas_pipes.core.cli import console, create_pipe_app, run_sync

app = create_pipe_app("Gmail commands.")


@app.command()
def auth(
    credentials: Path = typer.Argument(help="Path to Google OAuth client_secret.json file"),
) -> None:
    """Authenticate with Gmail via OAuth2.

    Download client_secret.json from Google Cloud Console:
    APIs & Services > Credentials > Create OAuth Client ID > Desktop app
    """
    from shenas_pipes.gmail.auth import build_client

    if not credentials.exists():
        console.print(f"[red]File not found: {credentials}[/red]")
        raise typer.Exit(code=1)

    console.print("Opening browser for Google authentication...", style="dim")
    try:
        service = build_client(client_secrets_path=str(credentials))
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

    try:
        service = build_client()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1)

    console.print("Syncing Gmail data...", style="dim")

    run_sync("gmail", "gmail", [messages(service, query), labels(service)], full_refresh)
