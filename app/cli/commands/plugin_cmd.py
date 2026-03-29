"""Shared install/uninstall/list/describe logic for all plugin types.

The data-returning functions (list_plugins_data, install_plugin, uninstall_plugin)
are called by both the REST API and the CLI display helpers below.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.request import urlopen

import typer
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from rich.console import Console
from rich.table import Table

from app.cli.client import ShenasClient, ShenasServerError
from repository.signing import load_public_key, verify_bytes

console = Console()

DEFAULT_INDEX = "http://127.0.0.1:7290"
PACKAGES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "packages"
PUBLIC_KEY_PATH = Path(".shenas") / "shenas.pub"

PREFIXES = {
    "pipe": "shenas-pipe-",
    "schema": "shenas-schema-",
    "component": "shenas-component-",
    "ui": "shenas-ui-",
}

SIG_STYLE = {
    "valid": "[green]verified[/green]",
    "invalid": "[red]INVALID[/red]",
    "unsigned": "[yellow]unsigned[/yellow]",
    "no key": "[dim]no key[/dim]",
}


# --- CLI display functions (call server) ---


def list_plugins(kind: str) -> None:
    """List plugins via the REST API and display as a rich table."""
    try:
        items = ShenasClient().plugins_list(kind)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if not items:
        console.print(f"[dim]No {kind} plugins installed[/dim]")
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
    """Install a plugin via the REST API."""
    try:
        result = ShenasClient().plugins_add(kind, [name], index_url=index_url, skip_verify=skip_verify)
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
    """Uninstall a plugin via the REST API."""
    try:
        result = ShenasClient().plugins_remove(kind, name)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if result["ok"]:
        console.print(f"[green]{result['message']}[/green]")
    else:
        console.print(f"[red]{result['message']}[/red]")
        raise typer.Exit(code=1)


def info(name: str, kind: str) -> None:
    """Show full info for an installed plugin."""
    try:
        result = ShenasClient().plugins_info(kind, name)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]{name}[/bold] ({kind})\n")

    desc = result.get("description", "")
    if desc:
        console.print(desc)
        console.print()

    from rich.table import Table

    table = Table(show_header=False, show_lines=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()

    enabled = result.get("enabled", True)
    table.add_row("Status", "[green]enabled[/green]" if enabled else "[yellow]disabled[/yellow]")
    if result.get("added_at"):
        table.add_row("Added", result["added_at"][:19])
    if result.get("updated_at"):
        table.add_row("Updated", result["updated_at"][:19])
    if result.get("enabled_at"):
        table.add_row("Enabled", result["enabled_at"][:19])
    if result.get("disabled_at"):
        table.add_row("Disabled", result["disabled_at"][:19])

    console.print(table)
    console.print()


def enable(name: str, kind: str) -> None:
    """Enable a plugin."""
    try:
        result = ShenasClient().plugins_enable(kind, name)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]{result.get('message', 'Enabled')}[/green]")


def disable(name: str, kind: str) -> None:
    """Disable a plugin."""
    try:
        result = ShenasClient().plugins_disable(kind, name)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[yellow]{result.get('message', 'Disabled')}[/yellow]")


def register_plugin_commands(parent_app: typer.Typer, kind: str, panel: str) -> list[dict[str, Any]]:
    """Discover installed plugins from the server and register subcommands.

    Registers commands based on what the server reports for each plugin.
    Returns the list of plugin info dicts for further processing by
    plugin-specific CLIs (e.g. pipes add sync/auth/config).
    """
    try:
        plugins = ShenasClient().plugins_list(kind)
    except Exception:
        return []

    for plugin in plugins:
        name = plugin["name"]
        commands = plugin.get("commands", [])
        plugin_app = typer.Typer(help=f"{name} {kind}.", invoke_without_command=True)

        @plugin_app.callback()
        def _default(ctx: typer.Context) -> None:
            if ctx.invoked_subcommand is None:
                typer.echo(ctx.get_help())
                raise typer.Exit()

        if "describe" in commands:
            _add_info(plugin_app, name, kind)

        parent_app.add_typer(plugin_app, name=name, rich_help_panel=panel)

    return plugins


def _add_info(plugin_app: typer.Typer, plugin_name: str, plugin_kind: str) -> None:
    @plugin_app.command("info")
    def _info() -> None:
        """Show info about this plugin."""
        info(plugin_name, plugin_kind)


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


def _verify_from_index(pkg_name: str, index_url: str, pub_key: Ed25519PublicKey) -> None:
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
        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
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
        console.print("The plugin may have been tampered with. Aborting.")
        raise typer.Exit(code=1)

    console.print("[green]Signature verified[/green]")
