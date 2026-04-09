from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from shenasctl.client import ShenasClient, ShenasServerError

console = Console()

app = typer.Typer(help="Transform commands.", invoke_without_command=True)

_TRANSFORM_FIELDS = (
    "id transformType sourceDuckdbSchema sourceDuckdbTable targetDuckdbSchema targetDuckdbTable "
    "sourcePlugin description params isDefault enabled addedAt updatedAt"
)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


@app.command("seed")
def seed_cmd() -> None:
    """Seed default transforms for all installed pipes."""
    try:
        data = ShenasClient()._graphql("mutation { seedTransforms }")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    seeded = data.get("seedTransforms") or []
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
        variables = {"source": source} if source else {}
        query = f"query($source: String) {{ transforms(source: $source) {{ {_TRANSFORM_FIELDS} }} }}"
        data = ShenasClient()._graphql(query, variables)
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    transforms = data.get("transforms", [])
    if not transforms:
        console.print("[dim]No transforms configured[/dim]")
        return

    table = Table(show_lines=False)
    table.add_column("ID", justify="right")
    table.add_column("Type")
    table.add_column("Source")
    table.add_column("Target")
    table.add_column("Description")
    table.add_column("Status")

    for t in transforms:
        source_label = f"{t['sourceDuckdbSchema']}.{t['sourceDuckdbTable']}"
        target_label = f"{t['targetDuckdbSchema']}.{t['targetDuckdbTable']}"
        status = "[green]enabled[/green]" if t.get("enabled", True) else "[yellow]disabled[/yellow]"
        default = " [dim](default)[/dim]" if t.get("isDefault") else ""
        table.add_row(
            str(t["id"]),
            t.get("transformType", "sql"),
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
    """Show a transform's details and params."""
    try:
        query = f"query($id: Int!) {{ transform(transformId: $id) {{ {_TRANSFORM_FIELDS} }} }}"
        data = ShenasClient()._graphql(query, {"id": transform_id})
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    t = data.get("transform")
    if not t:
        console.print(f"[red]Transform #{transform_id} not found[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]Transform #{t['id']}[/bold]")
    if t.get("description"):
        console.print(f"{t['description']}\n")

    table = Table(show_header=False, show_lines=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("Type", t.get("transformType", "sql"))
    table.add_row("Source", f"{t['sourceDuckdbSchema']}.{t['sourceDuckdbTable']}")
    table.add_row("Target", f"{t['targetDuckdbSchema']}.{t['targetDuckdbTable']}")
    table.add_row("Plugin", t["sourcePlugin"])
    table.add_row("Status", "[green]enabled[/green]" if t.get("enabled", True) else "[yellow]disabled[/yellow]")
    table.add_row("Default", "yes" if t.get("isDefault") else "no")
    if t.get("addedAt"):
        table.add_row("Added", t["addedAt"][:19])
    if t.get("updatedAt"):
        table.add_row("Updated", t["updatedAt"][:19])
    console.print(table)

    params = t.get("params", "{}")
    try:
        parsed = json.loads(params)
        console.print(f"\n[bold]Params:[/bold]\n{json.dumps(parsed, indent=2)}\n")
    except (json.JSONDecodeError, TypeError):
        console.print(f"\n[bold]Params:[/bold]\n{params}\n")


@app.command("test")
def test_cmd(
    transform_id: int = typer.Argument(help="Transform ID"),  # noqa: PT028
    limit: int = typer.Option(10, "--limit", help="Number of preview rows"),  # noqa: PT028
) -> None:
    """Preview a transform's output without writing to the target table."""
    try:
        data = ShenasClient()._graphql(
            "mutation($id: Int!, $limit: Int) { testTransform(transformId: $id, limit: $limit) }",
            {"id": transform_id, "limit": limit},
        )
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    rows = data.get("testTransform") or []
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
        ShenasClient()._graphql(
            f"mutation($id: Int!) {{ enableTransform(transformId: $id) {{ {_TRANSFORM_FIELDS} }} }}",
            {"id": transform_id},
        )
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
        ShenasClient()._graphql(
            f"mutation($id: Int!) {{ disableTransform(transformId: $id) {{ {_TRANSFORM_FIELDS} }} }}",
            {"id": transform_id},
        )
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[yellow]Disabled transform #{transform_id}[/yellow]")


@app.command("edit")
def edit_cmd(
    transform_id: int = typer.Argument(help="Transform ID"),
) -> None:
    """Edit a transform's params in $EDITOR."""
    import os
    import shlex
    import subprocess
    import tempfile
    from pathlib import Path

    try:
        query = f"query($id: Int!) {{ transform(transformId: $id) {{ {_TRANSFORM_FIELDS} }} }}"
        data = ShenasClient()._graphql(query, {"id": transform_id})
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    t = data.get("transform")
    if not t:
        console.print(f"[red]Transform #{transform_id} not found[/red]")
        raise typer.Exit(code=1)

    if t.get("isDefault"):
        console.print("[red]Default transforms cannot be edited[/red]")
        raise typer.Exit(code=1)

    import contextlib

    editor = os.environ.get("EDITOR", "vi")
    params_str = t.get("params", "{}")
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        params_str = json.dumps(json.loads(params_str), indent=2)

    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        f.write(params_str)
        f.flush()
        tmp_path = f.name

    subprocess.run([*shlex.split(editor), tmp_path], check=False)

    with open(tmp_path) as f:
        new_params = f.read().strip()

    Path(tmp_path).unlink()

    if new_params == params_str:
        console.print("[dim]No changes[/dim]")
        return

    try:
        ShenasClient()._graphql(
            "mutation($id: Int!, $params: String!) { updateTransform(transformId: $id, params: $params) { id } }",
            {"id": transform_id, "params": new_params},
        )
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
        ShenasClient()._graphql(
            "mutation($id: Int!) { deleteTransform(transformId: $id) { ok } }",
            {"id": transform_id},
        )
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]Deleted transform #{transform_id}[/green]")
