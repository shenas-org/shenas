from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import typer
from opentelemetry import trace
from rich.console import Console

console = Console()
logger = logging.getLogger("shenas.pipes")
tracer = trace.get_tracer("shenas.pipes")


def create_pipe_app(help_text: str) -> typer.Typer:
    """Create a standard pipe typer app with no-args-is-help callback."""
    app = typer.Typer(help=help_text, invoke_without_command=True)

    @app.callback()
    def _default(ctx: typer.Context) -> None:
        if ctx.invoked_subcommand is None:
            typer.echo(ctx.get_help())
            raise typer.Exit()

    return app


def print_load_info(load_info: Any) -> None:
    """Print completed job info from a dlt load result."""
    for package in load_info.load_packages:
        for job in package.jobs.get("completed_jobs", []):
            console.print(f"  [green]{job.job_file_info.table_name}[/green] -- {job.job_file_info.job_id()}")


def run_sync(
    pipeline_name: str,
    dataset_name: str,
    resources: list[Any],
    full_refresh: bool = False,
    transform_fn: Callable[[], None] | None = None,
) -> None:
    """Create a dlt pipeline, run it to memory, flush to encrypted DB, then transform.

    This handles the full sync lifecycle:
    1. Create an in-memory dlt DuckDB destination (data never on disk unencrypted)
    2. Run the pipeline with the given resources
    3. Flush in-memory data to the encrypted database
    4. Optionally run a transform function
    """
    logger.info("Sync started: %s (dataset=%s, full_refresh=%s)", pipeline_name, dataset_name, full_refresh)
    with tracer.start_as_current_span("pipe.sync", attributes={"pipe.name": pipeline_name, "pipe.dataset": dataset_name}):
        import dlt

        from shenas_pipes.core.db import DB_PATH, dlt_destination, flush_to_encrypted

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        with tracer.start_as_current_span("pipe.fetch"):
            logger.info("Fetching data: %s", pipeline_name)
            dest, mem_con = dlt_destination()

            pipeline = dlt.pipeline(
                pipeline_name=pipeline_name,
                destination=dest,
                dataset_name=dataset_name,
            )

            load_info = pipeline.run(resources, refresh="drop_sources" if full_refresh else None)
            print_load_info(load_info)
            logger.info("Fetch complete: %s (%d packages)", pipeline_name, len(load_info.load_packages))

        with tracer.start_as_current_span("pipe.flush"):
            logger.info("Flushing to encrypted database: %s", pipeline_name)
            console.print("Flushing to encrypted database...", style="dim")
            flush_to_encrypted(mem_con, dataset_name)

        if transform_fn:
            with tracer.start_as_current_span("pipe.transform"):
                logger.info("Running transforms: %s", pipeline_name)
                transform_fn()

        logger.info("Sync complete: %s", pipeline_name)
