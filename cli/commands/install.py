import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen

import typer
from rich.console import Console

from registry.signing import load_public_key, verify_bytes

console = Console()

app = typer.Typer(help="Install packages from the shenas repository.", invoke_without_command=True)

DEFAULT_INDEX = "http://127.0.0.1:8080"
PREFIXES = {"pipe": "shenas-pipe-", "schema": "shenas-schema-", "component": "shenas-component-"}


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def pipe(
    name: str = typer.Argument(help="Pipe name, e.g. 'garmin'"),
    index_url: str = typer.Option(DEFAULT_INDEX, "--index-url", help="Repository server URL"),
    public_key: Path = typer.Option(Path(".shenas/shenas.pub"), "--public-key", help="Path to Ed25519 public key for verification"),
    skip_verify: bool = typer.Option(False, "--skip-verify", help="Skip signature verification"),
) -> None:
    """Install a pipe package from the repository."""
    _install(name, "pipe", index_url, public_key, skip_verify)


def _install(name: str, kind: str, index_url: str, public_key_path: Path, skip_verify: bool) -> None:
    prefix = PREFIXES[kind]
    pkg_name = f"{prefix}{name}"

    if not skip_verify:
        if not public_key_path.exists():
            console.print(f"[red]Public key not found at {public_key_path}[/red]")
            console.print("Run [bold]shenas registry keygen[/bold] first, or use --skip-verify")
            raise typer.Exit(code=1)
        pub_key = load_public_key(public_key_path)
        _verify_from_index(pkg_name, index_url, pub_key)

    simple_url = f"{index_url}/simple/"
    result = subprocess.run(
        ["uv", "pip", "install", pkg_name, "--index-url", simple_url],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        console.print(f"[green]Installed {pkg_name}[/green]")
        if result.stdout.strip():
            console.print(result.stdout.strip(), style="dim")
    else:
        console.print(f"[red]Failed to install {pkg_name}[/red]")
        if result.stderr.strip():
            console.print(result.stderr.strip(), style="dim")
        raise typer.Exit(code=1)


def _verify_from_index(pkg_name: str, index_url: str, pub_key) -> None:
    """Fetch the wheel and its .sig from the index, verify before install."""
    from html.parser import HTMLParser

    # Discover the wheel filename from the simple index
    normalized = pkg_name.replace("_", "-").lower()
    simple_pkg_url = f"{index_url}/simple/{normalized}/"
    try:
        with urlopen(simple_pkg_url) as resp:
            html = resp.read().decode()
    except Exception as exc:
        console.print(f"[red]Cannot reach repository:[/red] {exc}")
        raise typer.Exit(code=1)

    wheel_href = None

    class LinkParser(HTMLParser):
        def handle_starttag(self, tag, attrs):
            nonlocal wheel_href
            if tag == "a":
                for attr_name, attr_val in attrs:
                    if attr_name == "href" and attr_val and ".whl" in attr_val:
                        wheel_href = attr_val.split("#")[0]

    LinkParser().feed(html)

    if not wheel_href:
        console.print(f"[red]No wheel found for {pkg_name} in repository[/red]")
        raise typer.Exit(code=1)

    # Take the last found (latest) wheel
    wheel_url = f"{index_url}{wheel_href}" if wheel_href.startswith("/") else f"{index_url}/{wheel_href}"
    sig_url = f"{wheel_url}.sig"

    console.print(f"Verifying [bold]{pkg_name}[/bold]...", style="dim")

    try:
        with urlopen(sig_url) as resp:
            sig_b64 = resp.read().decode().strip()
    except Exception:
        console.print(f"[red]No signature found for {pkg_name}[/red] ({sig_url})")
        console.print("Use --skip-verify to install without verification")
        raise typer.Exit(code=1)

    try:
        with urlopen(wheel_url) as resp:
            wheel_bytes = resp.read()
    except Exception as exc:
        console.print(f"[red]Cannot download wheel:[/red] {exc}")
        raise typer.Exit(code=1)

    if not verify_bytes(pub_key, wheel_bytes, sig_b64):
        console.print(f"[red]SIGNATURE VERIFICATION FAILED for {pkg_name}[/red]")
        console.print("The package may have been tampered with. Aborting.")
        raise typer.Exit(code=1)

    console.print(f"[green]Signature verified[/green]")
