from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from shenasctl.client import ShenasClient, ShenasServerError

console = Console()

app = typer.Typer(help="Transform commands.", invoke_without_command=True)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@app.command("seed")
def seed_cmd() -> None:
    """Seed default transforms for all installed pipes."""
    try:
        result = ShenasClient()._request("POST", "/api/transforms/seed")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    seeded = result.get("seeded", [])
    if seeded:
        console.print(f"[green]Seeded defaults for: {', '.join(seeded)}[/green]")
    else:
        console.print("[dim]All defaults already seeded[/dim]")


@app.command("list")
def list_cmd(
    source: str = typer.Option("", "--source", help="Filter by source plugin"),
) -> None:
    """List all transforms."""
    try:
        client = ShenasClient()
        params = f"?source={source}" if source else ""
        transforms = client._request("GET", f"/api/transforms{params}")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if not transforms:
        console.print("[dim]No transforms configured[/dim]")
        return

    table = Table(show_lines=False)
    table.add_column("ID", justify="right")
    table.add_column("Source")
    table.add_column("Target")
    table.add_column("Description")
    table.add_column("Status")

    for t in transforms:
        source_label = f"{t['source_duckdb_schema']}.{t['source_duckdb_table']}"
        target_label = f"{t['target_duckdb_schema']}.{t['target_duckdb_table']}"
        status = "[green]enabled[/green]" if t.get("enabled", True) else "[yellow]disabled[/yellow]"
        default = " [dim](default)[/dim]" if t.get("is_default") else ""
        table.add_row(
            str(t["id"]),
            source_label,
            target_label,
            (t.get("description") or "") + default,
            status,
        )
    console.print(table)


@app.command("show")
def show_cmd(
    transform_id: int = typer.Argument(help="Transform ID"),
) -> None:
    """Show a transform's details and SQL."""
    try:
        t = ShenasClient()._request("GET", f"/api/transforms/{transform_id}")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]Transform #{t['id']}[/bold]")
    if t.get("description"):
        console.print(f"{t['description']}\n")

    table = Table(show_header=False, show_lines=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Source", f"{t['source_duckdb_schema']}.{t['source_duckdb_table']}")
    table.add_row("Target", f"{t['target_duckdb_schema']}.{t['target_duckdb_table']}")
    table.add_row("Plugin", t["source_plugin"])
    table.add_row("Status", "[green]enabled[/green]" if t.get("enabled", True) else "[yellow]disabled[/yellow]")
    table.add_row("Default", "yes" if t.get("is_default") else "no")
    if t.get("added_at"):
        table.add_row("Added", t["added_at"][:19])
    if t.get("updated_at"):
        table.add_row("Updated", t["updated_at"][:19])
    console.print(table)
    console.print(f"\n[bold]SQL:[/bold]\n{t['sql']}\n")


@app.command("test")
def test_cmd(
    transform_id: int = typer.Argument(help="Transform ID"),
    limit: int = typer.Option(10, "--limit", help="Number of preview rows"),
) -> None:
    """Preview a transform's output without writing to the target table."""
    try:
        rows = ShenasClient()._request("POST", f"/api/transforms/{transform_id}/test?limit={limit}")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if not rows:
        console.print("[dim]No rows returned[/dim]")
        return

    table = Table(show_lines=False)
    for col in rows[0]:
        table.add_column(col)
    for row in rows:
        table.add_row(*[str(v) for v in row.values()])
    console.print(table)


@app.command("enable")
def enable_cmd(
    transform_id: int = typer.Argument(help="Transform ID"),
) -> None:
    """Enable a transform."""
    try:
        ShenasClient()._request("POST", f"/api/transforms/{transform_id}/enable")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]Enabled transform #{transform_id}[/green]")


@app.command("disable")
def disable_cmd(
    transform_id: int = typer.Argument(help="Transform ID"),
) -> None:
    """Disable a transform."""
    try:
        ShenasClient()._request("POST", f"/api/transforms/{transform_id}/disable")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[yellow]Disabled transform #{transform_id}[/yellow]")


@app.command("edit")
def edit_cmd(
    transform_id: int = typer.Argument(help="Transform ID"),
) -> None:
    """Edit a transform's SQL in $EDITOR."""
    import os
    import shlex
    import subprocess
    import tempfile

    try:
        t = ShenasClient()._request("GET", f"/api/transforms/{transform_id}")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    if t.get("is_default"):
        console.print("[red]Default transforms cannot be edited[/red]")
        raise typer.Exit(code=1)

    editor = os.environ.get("EDITOR", "vi")
    with tempfile.NamedTemporaryFile(suffix=".sql", mode="w", delete=False) as f:
        f.write(t["sql"])
        f.flush()
        tmp_path = f.name

    subprocess.run([*shlex.split(editor), tmp_path], check=False)

    with open(tmp_path) as f:
        new_sql = f.read().strip()

    os.unlink(tmp_path)

    if new_sql == t["sql"]:
        console.print("[dim]No changes[/dim]")
        return

    try:
        ShenasClient()._request("PUT", f"/api/transforms/{transform_id}", json={"sql": new_sql})
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]Updated transform #{transform_id}[/green]")


@app.command("delete")
def delete_cmd(
    transform_id: int = typer.Argument(help="Transform ID"),
) -> None:
    """Delete a user-created transform. Default transforms cannot be deleted."""
    try:
        ShenasClient()._request("DELETE", f"/api/transforms/{transform_id}")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]Deleted transform #{transform_id}[/green]")
