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
        import threading

        import dlt

        from shenas_pipes.core.db import DB_PATH, dlt_destination, flush_to_encrypted

        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        refresh = "drop_sources" if full_refresh else None
        total = len(resources)

        for i, resource in enumerate(resources):
            resource_name = getattr(resource, "name", None) or f"resource_{i}"
            with tracer.start_as_current_span("pipe.fetch", attributes={"resource": resource_name}):
                logger.info("Fetching %s (%d/%d): %s", pipeline_name, i + 1, total, resource_name)
                dest, mem_con = dlt_destination()

                pipeline = dlt.pipeline(
                    pipeline_name=pipeline_name,
                    destination=dest,
                    dataset_name=dataset_name,
                )

                load_result: list[Any] = []
                load_error: list[Exception] = []

                def _run(res: Any = resource, ref: str = refresh if i == 0 else None) -> None:
                    try:
                        load_result.append(pipeline.run(res, refresh=ref))
                    except Exception as exc:
                        load_error.append(exc)

                t = threading.Thread(target=_run, daemon=True)
                t.start()
                elapsed = 0
                while t.is_alive():
                    t.join(timeout=10)
                    if t.is_alive():
                        elapsed += 10
                        logger.info("Still fetching %s/%s... (%ds elapsed)", pipeline_name, resource_name, elapsed)

                if load_error:
                    logger.error("Fetch failed for %s/%s: %s", pipeline_name, resource_name, load_error[0])
                    raise load_error[0]
                if not load_result:
                    logger.error("Fetch returned no result for %s/%s", pipeline_name, resource_name)
                    raise RuntimeError(f"pipeline.run() returned no result for {resource_name}")

                print_load_info(load_result[0])
                logger.info("Fetch complete: %s/%s", pipeline_name, resource_name)

            with tracer.start_as_current_span("pipe.flush", attributes={"resource": resource_name}):
                logger.info("Flushing %s/%s to encrypted database", pipeline_name, resource_name)
                flush_to_encrypted(mem_con, dataset_name)

            # Only apply refresh on the first resource
            refresh = None

        if transform_fn:
            with tracer.start_as_current_span("pipe.transform"):
                logger.info("Running transforms: %s", pipeline_name)
                transform_fn()

        logger.info("Sync complete: %s", pipeline_name)
