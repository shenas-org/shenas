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
    pipeline: Any,
    resources: list,
    full_refresh: bool,
    transform_fn: Callable[[], None] | None = None,
) -> None:
    """Run a dlt pipeline, print results, and optionally transform."""
    load_info = pipeline.run(resources, refresh="drop_sources" if full_refresh else None)
    print_load_info(load_info)
    if transform_fn:
        transform_fn()
