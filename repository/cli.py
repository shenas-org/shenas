"""Registry CLI commands: keygen, sign, verify."""

from pathlib import Path

import typer
from rich.console import Console

from repository.signing import generate_keypair, load_private_key, load_public_key, verify_file, write_signature

console = Console()

app = typer.Typer(help="Registry key management and package signing.", invoke_without_command=True)

DEFAULT_KEY_DIR = Path(".shenas")


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command()
def keygen(
    key_dir: Path = typer.Option(DEFAULT_KEY_DIR, help="Directory to write keypair"),
) -> None:
    """Generate an Ed25519 signing keypair."""
    priv_path, pub_path = generate_keypair(key_dir)
    console.print(f"[green]Private key:[/green] {priv_path}")
    console.print(f"[green]Public key:[/green]  {pub_path}")
    console.print(f"\nKeep [bold]{priv_path}[/bold] secret. Distribute [bold]{pub_path}[/bold] with your CLI.")


@app.command()
def sign(
    wheel: Path = typer.Argument(help="Path to .whl file to sign"),
    private_key: Path = typer.Option(DEFAULT_KEY_DIR / "shenas.key", "--key", help="Path to Ed25519 private key"),
) -> None:
    """Sign a wheel file, creating a .sig file next to it."""
    if not wheel.exists():
        console.print(f"[red]File not found: {wheel}[/red]")
        raise typer.Exit(code=1)
    if not private_key.exists():
        console.print(f"[red]Private key not found: {private_key}[/red]")
        console.print("Run [bold]shenasrepoctl keygen[/bold] first.")
        raise typer.Exit(code=1)

    key = load_private_key(private_key)
    sig_path = write_signature(key, wheel)
    console.print(f"[green]Signed:[/green] {sig_path}")


@app.command()
def verify(
    wheel: Path = typer.Argument(help="Path to .whl file to verify"),
    public_key: Path = typer.Option(DEFAULT_KEY_DIR / "shenas.pub", "--public-key", help="Path to Ed25519 public key"),
) -> None:
    """Verify a wheel's signature."""
    sig_path = wheel.with_suffix(wheel.suffix + ".sig")
    if not sig_path.exists():
        console.print(f"[red]No signature file found: {sig_path}[/red]")
        raise typer.Exit(code=1)

    pub_key = load_public_key(public_key)
    sig_b64 = sig_path.read_text().strip()

    if verify_file(pub_key, wheel, sig_b64):
        console.print("[green]Valid signature[/green]")
    else:
        console.print("[red]INVALID signature[/red]")
        raise typer.Exit(code=1)


@app.command("sign-all")
def sign_all(
    packages_dir: Path = typer.Argument(Path("packages"), help="Directory containing .whl files"),
    private_key: Path = typer.Option(DEFAULT_KEY_DIR / "shenas.key", "--key", help="Path to Ed25519 private key"),
) -> None:
    """Sign all unsigned wheels in a directory."""
    if not packages_dir.is_dir():
        console.print(f"[red]Directory not found: {packages_dir}[/red]")
        raise typer.Exit(code=1)

    key = load_private_key(private_key)
    signed = 0
    for whl in sorted(packages_dir.glob("*.whl")):
        sig_path = whl.with_suffix(whl.suffix + ".sig")
        if not sig_path.exists():
            write_signature(key, whl)
            console.print(f"[green]Signed:[/green] {whl.name}")
            signed += 1
    if signed == 0:
        console.print("[dim]No unsigned wheels found.[/dim]")
    else:
        console.print(f"\n[green]Signed {signed} wheel(s).[/green]")


@app.command()
def vendor(
    pipe: str = typer.Argument(help="Pipe name, e.g. 'garmin'"),
    packages_dir: Path = typer.Option(Path("packages"), "--dest", help="Destination directory"),
) -> None:
    """Download a pipe wheel and all its transitive dependencies."""
    import subprocess

    packages_dir.mkdir(parents=True, exist_ok=True)
    pkg_name = f"shenas-pipe-{pipe}"
    result = subprocess.run(
        ["uv", "pip", "download", pkg_name, "--dest", str(packages_dir), "--find-links", str(packages_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        console.print(f"[green]Vendored {pkg_name} and dependencies into {packages_dir}[/green]")
    else:
        console.print(f"[red]Failed to vendor {pkg_name}[/red]")
        if result.stderr.strip():
            console.print(result.stderr.strip(), style="dim")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
