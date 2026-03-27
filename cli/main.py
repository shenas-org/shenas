import typer

from cli.commands import component, data, pipe, registry_cmd, schema_cmd, ui

app = typer.Typer(name="shenas", invoke_without_command=True)
app.add_typer(pipe.app, name="pipe")
app.add_typer(component.app, name="component")
app.add_typer(schema_cmd.app, name="schema")
app.add_typer(data.app, name="data")
app.add_typer(ui.app, name="ui")
app.add_typer(registry_cmd.app, name="registry")


@app.callback()
def root(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def main() -> None:
    app()
