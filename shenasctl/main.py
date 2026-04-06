from __future__ import annotations

import typer

from shenasctl.commands import (
    config_cmd,
    dashboard,
    dataset_cmd,
    db_cmd,
    frontend_cmd,
    service,
    source,
    theme_cmd,
    transform_cmd,
)

app = typer.Typer(name="shenasctl", invoke_without_command=True)
app.add_typer(source.app, name="source")
app.add_typer(dashboard.app, name="dashboard")
app.add_typer(frontend_cmd.app, name="frontend")
app.add_typer(theme_cmd.app, name="theme")
app.add_typer(dataset_cmd.app, name="dataset")
app.add_typer(config_cmd.app, name="config")
app.add_typer(db_cmd.app, name="db")
app.add_typer(transform_cmd.app, name="transform")
app.add_typer(service.app, name="service")


@app.callback()
def root(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


def main() -> None:
    app()
