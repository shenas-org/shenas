"""Shared install/uninstall/list logic for all package types (used by API server).

The data-returning functions (list_packages_data, install_package, uninstall_package)
are called by both the REST API and the CLI display helpers below.
"""

from pathlib import Path
from urllib.request import urlopen

import typer
from rich.console import Console
from rich.table import Table

from cli.client import ShenasClient, ShenasServerError
from repository.signing import load_public_key, verify_bytes

console = Console()

DEFAULT_INDEX = "http://127.0.0.1:7290"
PACKAGES_DIR = Path(__file__).resolve().parent.parent.parent / "packages"
PUBLIC_KEY_PATH = Path(".shenas") / "shenas.pub"

PREFIXES = {
    "pipe": "shenas-pipe-",
    "schema": "shenas-schema-",
    "component": "shenas-component-",
}

SIG_STYLE = {
    "valid": "[green]verified[/green]",
    "invalid": "[red]INVALID[/red]",
    "unsigned": "[yellow]unsigned[/yellow]",
    "no key": "[dim]no key[/dim]",
}


# --- CLI display functions (call server) ---


def list_packages(kind: str) -> None:
    """List packages via the REST API and display as a rich table."""
    try:
        items = ShenasClient().packages_list(kind)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if not items:
        console.print(f"[dim]No {kind} packages installed[/dim]")
        return

    table = Table(show_lines=False)
    table.add_column(kind.capitalize(), style="green")
    table.add_column("Package")
    table.add_column("Version", justify="right")
    table.add_column("Signature", justify="right")
    for p in items:
        table.add_row(p["name"], p["package"], p["version"], SIG_STYLE.get(p["signature"], p["signature"]))
    console.print(table)


def install(
    name: str,
    kind: str,
    index_url: str = DEFAULT_INDEX,
    skip_verify: bool = False,
) -> None:
    """Install a package via the REST API."""
    try:
        result = ShenasClient().packages_add(kind, [name], index_url=index_url, skip_verify=skip_verify)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    for r in result.get("results", []):
        if r["ok"]:
            console.print(f"[green]{r['message']}[/green]")
        else:
            console.print(f"[red]{r['message']}[/red]")
            raise typer.Exit(code=1)


def uninstall(name: str, kind: str) -> None:
    """Uninstall a package via the REST API."""
    try:
        result = ShenasClient().packages_remove(kind, name)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if result["ok"]:
        console.print(f"[green]{result['message']}[/green]")
    else:
        console.print(f"[red]{result['message']}[/red]")
        raise typer.Exit(code=1)


# --- Signature checking (used by API server) ---


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
    from repository.signing import verify_file

    return "valid" if verify_file(pub_key, wheel_path, sig_b64) else "invalid"


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
