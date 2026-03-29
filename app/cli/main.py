from __future__ import annotations

import typer

from app.cli.commands import component, config_cmd, db_cmd, pipe, schema_cmd, ui_cmd

app = typer.Typer(name="shenasctl", invoke_without_command=True)
app.add_typer(pipe.app, name="pipe")
app.add_typer(component.app, name="component")
app.add_typer(ui_cmd.app, name="ui")
app.add_typer(schema_cmd.app, name="schema")
app.add_typer(config_cmd.app, name="config")
app.add_typer(db_cmd.app, name="db")


@app.callback()
def root(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def main() -> None:
    app()
