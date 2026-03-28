"""Shared install/uninstall/list logic for all package types."""

import json
import subprocess
from pathlib import Path
from urllib.request import urlopen

import typer
from rich.console import Console
from rich.table import Table

from registry.signing import load_public_key, verify_bytes

console = Console()

DEFAULT_INDEX = "http://127.0.0.1:8080"
PACKAGES_DIR = Path(__file__).resolve().parent.parent.parent / "packages"
PUBLIC_KEY_PATH = Path(".shenas") / "shenas.pub"

PREFIXES = {
    "pipe": "shenas-pipe-",
    "schema": "shenas-schema-",
    "component": "shenas-component-",
}


def install(
    name: str,
    kind: str,
    index_url: str = DEFAULT_INDEX,
    public_key_path: Path = Path(".shenas/shenas.pub"),
    skip_verify: bool = False,
) -> None:
    if name == "core":
        console.print(f"[red]shenas-{kind}-core is an internal package and cannot be installed directly.[/red]")
        raise typer.Exit(code=1)

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


def uninstall(name: str, kind: str) -> None:
    if name == "core":
        console.print(f"[red]shenas-{kind}-core is an internal package and cannot be removed directly.[/red]")
        raise typer.Exit(code=1)

    pkg_name = f"{PREFIXES[kind]}{name}"

    result = subprocess.run(
        ["uv", "pip", "uninstall", pkg_name],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        console.print(f"[green]Uninstalled {pkg_name}[/green]")
        if result.stdout.strip():
            console.print(result.stdout.strip(), style="dim")
    else:
        console.print(f"[red]Failed to uninstall {pkg_name}[/red]")
        if result.stderr.strip():
            console.print(result.stderr.strip(), style="dim")
        raise typer.Exit(code=1)


def list_packages(kind: str) -> None:
    prefix = PREFIXES[kind]
    result = subprocess.run(["uv", "pip", "list", "--format", "json"], capture_output=True, text=True)
    if result.returncode != 0:
        console.print("[red]Failed to list packages[/red]")
        raise typer.Exit(code=1)

    packages = json.loads(result.stdout)
    matched = [p for p in packages if p["name"].startswith(prefix) and not p["name"].endswith("-core")]

    if not matched:
        console.print(f"[dim]No {kind} packages installed[/dim]")
        return

    table = Table(show_lines=False)
    table.add_column(kind.capitalize(), style="green")
    table.add_column("Package")
    table.add_column("Version", justify="right")
    table.add_column("Signature", justify="right")
    for p in sorted(matched, key=lambda x: x["name"]):
        short_name = p["name"].removeprefix(prefix)
        sig_status = check_signature(p["name"], p["version"])
        table.add_row(short_name, p["name"], p["version"], SIG_STYLE[sig_status])
    console.print(table)


def check_signature(pkg_name: str, version: str) -> str:
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

    pub_key = load_public_key(PUBLIC_KEY_PATH)
    sig_b64 = sig_path.read_text().strip()
    from registry.signing import verify_file

    return "valid" if verify_file(pub_key, wheel_path, sig_b64) else "invalid"


SIG_STYLE = {
    "valid": "[green]verified[/green]",
    "invalid": "[red]INVALID[/red]",
    "unsigned": "[yellow]unsigned[/yellow]",
    "no key": "[dim]no key[/dim]",
}


def _verify_from_index(pkg_name: str, index_url: str, pub_key) -> None:
    from html.parser import HTMLParser

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

    console.print("[green]Signature verified[/green]")
