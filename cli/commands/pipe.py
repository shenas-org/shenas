import json
import subprocess
from importlib.metadata import entry_points
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

app = typer.Typer(help="Pipeline commands.", invoke_without_command=True)

PACKAGES_DIR = Path(__file__).resolve().parent.parent.parent / "packages"
PUBLIC_KEY_PATH = Path(".shenas") / "shenas.pub"

for _ep in entry_points(group="shenas.pipes"):
    app.add_typer(_ep.load(), name=_ep.name)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _check_signature(pkg_name: str, version: str) -> str:
    """Check if a wheel has a valid signature in the packages dir."""
    if not PUBLIC_KEY_PATH.exists():
        return "no key"

    normalized = pkg_name.replace("-", "_")
    matches = list(PACKAGES_DIR.glob(f"{normalized}-{version}*.whl")) if PACKAGES_DIR.is_dir() else []
    if not matches:
        return "unsigned"

    wheel_path = matches[0]
    sig_path = wheel_path.with_suffix(wheel_path.suffix + ".sig")
    if not sig_path.exists():
        return "unsigned"

    from registry.signing import load_public_key, verify_file

    pub_key = load_public_key(PUBLIC_KEY_PATH)
    sig_b64 = sig_path.read_text().strip()
    return "valid" if verify_file(pub_key, wheel_path, sig_b64) else "invalid"


_SIG_STYLE = {
    "valid": "[green]verified[/green]",
    "invalid": "[red]INVALID[/red]",
    "unsigned": "[yellow]unsigned[/yellow]",
    "no key": "[dim]no key[/dim]",
}


@app.command("list")
def list_pipes() -> None:
    """List installed pipe packages."""
    result = subprocess.run(["uv", "pip", "list", "--format", "json"], capture_output=True, text=True)
    if result.returncode != 0:
        console.print("[red]Failed to list packages[/red]")
        raise typer.Exit(code=1)

    packages = json.loads(result.stdout)
    pipes = [p for p in packages if p["name"].startswith("shenas-pipe-")]

    if not pipes:
        console.print("[dim]No pipe packages installed[/dim]")
        return

    table = Table(show_lines=False)
    table.add_column("Pipe", style="green")
    table.add_column("Package")
    table.add_column("Version", justify="right")
    table.add_column("Signature", justify="right")
    for p in sorted(pipes, key=lambda x: x["name"]):
        short_name = p["name"].removeprefix("shenas-pipe-")
        sig_status = _check_signature(p["name"], p["version"])
        table.add_row(short_name, p["name"], p["version"], _SIG_STYLE[sig_status])
    console.print(table)
