from pathlib import Path

import typer
from rich.console import Console

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
    from registry.signing import generate_keypair

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
    from registry.signing import load_private_key, write_signature

    if not wheel.exists():
        console.print(f"[red]File not found: {wheel}[/red]")
        raise typer.Exit(code=1)
    if not private_key.exists():
        console.print(f"[red]Private key not found: {private_key}[/red]")
        console.print("Run [bold]shenas registry keygen[/bold] first.")
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
    from registry.signing import load_public_key, verify_file

    sig_path = wheel.with_suffix(wheel.suffix + ".sig")
    if not sig_path.exists():
        console.print(f"[red]No signature file found: {sig_path}[/red]")
        raise typer.Exit(code=1)

    pub_key = load_public_key(public_key)
    sig_b64 = sig_path.read_text().strip()

    if verify_file(pub_key, wheel, sig_b64):
        console.print(f"[green]Valid signature[/green]")
    else:
        console.print(f"[red]INVALID signature[/red]")
        raise typer.Exit(code=1)
