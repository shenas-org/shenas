import importlib
import importlib.util
import json
import subprocess
import sys
from importlib.metadata import entry_points
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

console = Console()

app = typer.Typer(help="Pipeline commands.", invoke_without_command=True)

PIPES_DIR = Path(__file__).resolve().parent.parent.parent / "pipes"


def _load_from_entry_points() -> None:
    for ep in entry_points(group="shenas.pipes"):
        app.add_typer(ep.load(), name=ep.name)


def _load_from_disk() -> None:
    if not PIPES_DIR.is_dir():
        return
    for pipe_dir in sorted(PIPES_DIR.iterdir()):
        src_dir = pipe_dir / "src"
        if not src_dir.is_dir():
            continue
        name = pipe_dir.name
        cli_path = src_dir / "shenas_pipes" / name / "cli.py"
        if not cli_path.is_file():
            continue
        # Add src/ to sys.path for transitive imports within the pipe
        src_str = str(src_dir)
        if src_str not in sys.path:
            sys.path.insert(0, src_str)
        # Load the cli module directly by file path
        mod_name = f"shenas_pipes.{name}.cli"
        spec = importlib.util.spec_from_file_location(mod_name, cli_path, submodule_search_locations=[])
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            try:
                spec.loader.exec_module(mod)
                app.add_typer(mod.app, name=name)
                _dev_loaded.add(name)
            except Exception as exc:
                print(f"[dev] Failed to load pipe {name}: {exc}", file=sys.stderr)
                sys.modules.pop(mod_name, None)


PACKAGES_DIR = Path(__file__).resolve().parent.parent.parent / "packages"
PUBLIC_KEY_PATH = Path(".shenas") / "shenas.pub"

# Track which pipes were loaded from disk (--dev mode)
_dev_loaded: set[str] = set()

if "--dev" in sys.argv:
    _load_from_disk()
else:
    _load_from_entry_points()


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _check_signature(pkg_name: str, version: str) -> str:
    """Check if a wheel has a valid signature in the packages dir.

    Returns: 'valid', 'invalid', 'unsigned', or 'no key'.
    """
    if not PUBLIC_KEY_PATH.exists():
        return "no key"

    # Find the wheel in packages/
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
    "dev": "[cyan]dev[/cyan]",
}


@app.command("list")
def list_pipes() -> None:
    """List installed pipe packages."""
    dev_mode = "--dev" in sys.argv

    if dev_mode:
        # Show dev-loaded pipes
        table = Table(show_lines=False)
        table.add_column("Pipe", style="green")
        table.add_column("Source")
        table.add_column("Signature", justify="right")
        for name in sorted(_dev_loaded):
            src_dir = PIPES_DIR / name / "src"
            table.add_row(name, str(src_dir), _SIG_STYLE["dev"])
        if not _dev_loaded:
            console.print("[dim]No dev pipes loaded[/dim]")
            return
        console.print(table)
        return

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
