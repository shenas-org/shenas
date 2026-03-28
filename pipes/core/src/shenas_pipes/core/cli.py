from typing import Any, Callable

import typer
from rich.console import Console

console = Console()


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
    resources: list,
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
    import dlt

    from shenas_pipes.core.db import DB_PATH, dlt_destination, flush_to_encrypted

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # TEMPORARY WORKAROUND: dlt does not support DuckDB encryption. We write to
    # in-memory DuckDB (data never touches disk unencrypted), then flush to the
    # encrypted file. Replace when dlt adds DuckDB encryption support.
    dest, mem_con = dlt_destination()

    pipeline = dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=dest,
        dataset_name=dataset_name,
    )

    load_info = pipeline.run(resources, refresh="drop_sources" if full_refresh else None)
    print_load_info(load_info)

    console.print("Flushing to encrypted database...", style="dim")
    flush_to_encrypted(mem_con, dataset_name)

    if transform_fn:
        transform_fn()
