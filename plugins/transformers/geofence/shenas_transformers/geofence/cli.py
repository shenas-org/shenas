from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from shenasctl.client import ShenasClient, ShenasServerError

console = Console()

app = typer.Typer(help="Geofence commands.", invoke_without_command=True)

_GEOFENCE_FIELDS = "id name latitude longitude radiusM category addedAt updatedAt"


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


@app.command("list")
def list_cmd() -> None:
    """List all geofences."""
    try:
        data = ShenasClient()._graphql(f"query {{ geofences {{ {_GEOFENCE_FIELDS} }} }}")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    geofences = data.get("geofences", [])
    if not geofences:
        console.print("[dim]No geofences configured[/dim]")
        return

    table = Table(show_lines=False)
    table.add_column("ID", justify="right")
    table.add_column("Name")
    table.add_column("Latitude", justify="right")
    table.add_column("Longitude", justify="right")
    table.add_column("Radius (m)", justify="right")
    table.add_column("Category")

    for g in geofences:
        table.add_row(
            str(g["id"]),
            g["name"],
            f"{g['latitude']:.6f}",
            f"{g['longitude']:.6f}",
            f"{g['radiusM']:.0f}",
            g.get("category") or "",
        )
    console.print(table)


@app.command("add")
def add_cmd(
    name: str = typer.Argument(help="Geofence name (e.g. Home, Work, Library)"),
    latitude: float = typer.Argument(help="Center latitude"),
    longitude: float = typer.Argument(help="Center longitude"),
    radius_m: float = typer.Option(200.0, "--radius", help="Radius in meters"),
    category: str = typer.Option("", "--category", help="Optional category"),
) -> None:
    """Add a new geofence."""
    try:
        data = ShenasClient()._graphql(
            f"""mutation($input: GeofenceCreateInput!) {{
                createGeofence(geofenceInput: $input) {{ {_GEOFENCE_FIELDS} }}
            }}""",
            {
                "input": {
                    "name": name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "radiusM": radius_m,
                    "category": category,
                }
            },
        )
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    g = data.get("createGeofence", {})
    console.print(f"[green]Created geofence #{g.get('id')}: {g.get('name')}[/green]")


@app.command("update")
def update_cmd(
    geofence_id: int = typer.Argument(help="Geofence ID"),
    name: str | None = typer.Option(None, "--name", help="New name"),
    latitude: float | None = typer.Option(None, "--latitude", help="New latitude"),
    longitude: float | None = typer.Option(None, "--longitude", help="New longitude"),
    radius_m: float | None = typer.Option(None, "--radius", help="New radius in meters"),
    category: str | None = typer.Option(None, "--category", help="New category"),
) -> None:
    """Update an existing geofence."""
    update_input: dict[str, str | float] = {}
    if name is not None:
        update_input["name"] = name
    if latitude is not None:
        update_input["latitude"] = latitude
    if longitude is not None:
        update_input["longitude"] = longitude
    if radius_m is not None:
        update_input["radiusM"] = radius_m
    if category is not None:
        update_input["category"] = category

    if not update_input:
        console.print("[yellow]No fields to update[/yellow]")
        raise typer.Exit

    try:
        data = ShenasClient()._graphql(
            f"""mutation($id: Int!, $input: GeofenceUpdateInput!) {{
                updateGeofence(geofenceId: $id, geofenceInput: $input) {{ {_GEOFENCE_FIELDS} }}
            }}""",
            {"id": geofence_id, "input": update_input},
        )
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    g = data.get("updateGeofence")
    if not g:
        console.print(f"[red]Geofence #{geofence_id} not found[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]Updated geofence #{g['id']}: {g['name']}[/green]")


@app.command("delete")
def delete_cmd(
    geofence_id: int = typer.Argument(help="Geofence ID"),
) -> None:
    """Delete a geofence."""
    try:
        ShenasClient()._graphql(
            "mutation($id: Int!) { deleteGeofence(geofenceId: $id) { ok } }",
            {"id": geofence_id},
        )
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
    console.print(f"[green]Deleted geofence #{geofence_id}[/green]")
