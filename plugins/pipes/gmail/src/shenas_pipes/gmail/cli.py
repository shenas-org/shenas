from __future__ import annotations

import logging

import typer

from shenas_pipes.core.cli import console, create_pipe_app

app = create_pipe_app("Gmail commands.")

DISPLAY_NAME = "Gmail"
DESCRIPTION = """Syncs email metadata from Gmail.

Uses Google OAuth2 with shared credentials from shenas-pipe-core.
Authorization URL is passed back to the CLI for browser-based consent."""

logger = logging.getLogger(__name__)


@app.command()
def auth() -> None:
    """Authenticate with Gmail via OAuth2. Opens browser for Google login."""
    from shenas_pipes.gmail.auth import build_client

    console.print("Opening browser for Google authentication...", style="dim")
    try:
        service = build_client(run_auth_flow=True)
        profile = service.users().getProfile(userId="me").execute()
        console.print(f"[green]Authenticated as {profile['emailAddress']}[/green]")
        console.print("[green]Token saved to database[/green]")
    except Exception as exc:
        console.print(f"[red]Authentication failed:[/red] {exc}")
        raise typer.Exit(code=1)


@app.command()
def sync(
    query: str = typer.Option("", "--query", "-q", help="Gmail search query (e.g. 'after:2026/01/01')"),
    full_refresh: bool = typer.Option(False, "--full-refresh", help="Drop all data and re-download."),
) -> None:
    """Sync Gmail messages into DuckDB, flushing each page to disk."""
    import dlt
    from opentelemetry import trace

    from shenas_pipes.core.cli import print_load_info
    from shenas_pipes.core.db import DB_PATH, dlt_destination, flush_to_encrypted
    from shenas_pipes.gmail.auth import build_client
    from shenas_pipes.gmail.source import labels, message_pages

    tracer = trace.get_tracer("shenas.pipes")
    service = build_client()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Sync started: gmail (dataset=gmail, full_refresh=%s)", full_refresh)

    with tracer.start_as_current_span("pipe.sync", attributes={"pipe.name": "gmail"}):
        page_num = 0
        total_msgs = 0

        for page in message_pages(service, query):
            page_num += 1

            with tracer.start_as_current_span("pipe.fetch", attributes={"resource": "messages", "page": page_num}):
                dest, mem_con = dlt_destination()
                pipeline = dlt.pipeline(pipeline_name="gmail", destination=dest, dataset_name="gmail")

                @dlt.resource(name="messages", write_disposition="merge", primary_key="id")
                def _page_data(_data=tuple(page)):
                    yield from _data

                ref = "drop_sources" if full_refresh and page_num == 1 else None
                load_info = pipeline.run(_page_data(), refresh=ref)
                print_load_info(load_info)

            with tracer.start_as_current_span("pipe.flush", attributes={"resource": "messages", "page": page_num}):
                flush_to_encrypted(mem_con, "gmail")
                total_msgs += len(page)
                logger.info("Flushed page %d (%d messages, %d total)", page_num, len(page), total_msgs)

        # Sync labels (small, single pass)
        with tracer.start_as_current_span("pipe.fetch", attributes={"resource": "labels"}):
            dest, mem_con = dlt_destination()
            pipeline = dlt.pipeline(pipeline_name="gmail", destination=dest, dataset_name="gmail")
            load_info = pipeline.run(labels(service))
            print_load_info(load_info)

        with tracer.start_as_current_span("pipe.flush", attributes={"resource": "labels"}):
            flush_to_encrypted(mem_con, "gmail")

        logger.info("Sync complete: gmail (%d messages in %d pages)", total_msgs, page_num)
