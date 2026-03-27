import typer
import uvicorn

app = typer.Typer(help="Start the shenas UI server.", invoke_without_command=True)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        serve(host="127.0.0.1", port=8000)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
) -> None:
    """Start the UI web server."""
    from local_frontend.server import app as fastapi_app

    uvicorn.run(fastapi_app, host=host, port=port)
