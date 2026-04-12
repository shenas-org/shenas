"""CLI commands for LLM-driven suggestions."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from shenasctl.client import ShenasClient, ShenasServerError

console = Console()

app = typer.Typer(help="LLM suggestion commands.", invoke_without_command=True)


@app.callback()
def _default(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit


@app.command("datasets")
def datasets_cmd(
    source: str = typer.Option("", "--source", help="Filter by source plugin"),
) -> None:
    """Ask LLM to suggest canonical metric tables + transforms."""
    try:
        variables: dict[str, str | None] = {"source": source or None}
        data = ShenasClient()._graphql(
            "mutation($source: String) { suggestDatasets(source: $source) }",
            variables,
        )
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    result = data.get("suggestDatasets", {})
    if not result.get("ok"):
        console.print(f"[red]{result.get('error', 'Unknown error')}[/red]")
        raise typer.Exit(code=1)

    suggestions = result.get("suggestions", [])
    if not suggestions:
        console.print("[dim]No suggestions generated[/dim]")
        return

    console.print(f"\n[bold]Suggested datasets[/bold] (batch {result.get('batch_id', '')})\n")
    for s in suggestions:
        console.print(f"  [green]{s['name']}[/green] ({s['grain']})")
        console.print(f"    {s.get('title', '')}")
        console.print(f"    {s.get('description', '')}")
        console.print(f"    {s['column_count']} columns, {s['transform_count']} transforms")
        console.print()

    cost = result.get("cost", {})
    if cost:
        console.print(
            f"[dim]Tokens: {cost.get('llm_input_tokens', 0)} in / "
            f"{cost.get('llm_output_tokens', 0)} out | "
            f"{cost.get('wall_clock_ms', 0):.0f}ms[/dim]"
        )


@app.command("analyses")
def analyses_cmd() -> None:
    """Ask LLM to suggest interesting analyses given current datasets."""
    try:
        data = ShenasClient()._graphql("mutation { suggestAnalyses }")
    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)

    result = data.get("suggestAnalyses", {})
    if not result.get("ok"):
        console.print(f"[red]{result.get('error', 'Unknown error')}[/red]")
        raise typer.Exit(code=1)

    suggestions = result.get("suggestions", [])
    if not suggestions:
        console.print("[dim]No suggestions generated[/dim]")
        return

    console.print(f"\n[bold]Suggested analyses[/bold] (batch {result.get('batch_id', '')})\n")
    for s in suggestions:
        complexity = f" [{s['complexity']}]" if s.get("complexity") else ""
        console.print(f"  [green]#{s['id']}[/green]{complexity}")
        console.print(f"    {s['question']}")
        console.print(f"    [dim]{s.get('rationale', '')}[/dim]")
        if s.get("datasets_involved"):
            console.print(f"    [dim]Tables: {', '.join(s['datasets_involved'])}[/dim]")
        console.print()


@app.command("list")
def list_cmd(
    kind: str = typer.Option("", "--kind", help="Filter by kind (dataset, transform, analysis)"),
) -> None:
    """List pending suggestions."""
    try:
        client = ShenasClient()
        has_output = False

        if not kind or kind == "dataset":
            data = client._graphql("{ suggestedDatasets }")
            datasets = data.get("suggestedDatasets", [])
            if datasets:
                has_output = True
                table = Table(title="Suggested Datasets", show_lines=False)
                table.add_column("Name")
                table.add_column("Grain")
                table.add_column("Description")
                for d in datasets:
                    table.add_row(d["name"], d.get("grain", ""), d.get("description", "")[:60])
                console.print(table)

        if not kind or kind == "transform":
            data = client._graphql("{ suggestedTransforms }")
            transforms = data.get("suggestedTransforms", [])
            if transforms:
                has_output = True
                table = Table(title="Suggested Transforms", show_lines=False)
                table.add_column("ID", justify="right")
                table.add_column("Source")
                table.add_column("Target")
                table.add_column("Description")
                for t in transforms:
                    table.add_row(str(t["id"]), t["source"], t["target"], t.get("description", "")[:60])
                console.print(table)

        if not kind or kind == "analysis":
            data = client._graphql("{ suggestedAnalyses }")
            analyses = data.get("suggestedAnalyses", [])
            if analyses:
                has_output = True
                table = Table(title="Suggested Analyses", show_lines=False)
                table.add_column("ID", justify="right")
                table.add_column("Question")
                table.add_column("Complexity")
                for a in analyses:
                    table.add_row(str(a["id"]), a["question"][:70], a.get("complexity", ""))
                console.print(table)

        if not has_output:
            console.print("[dim]No pending suggestions[/dim]")

    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)


@app.command("accept")
def accept_cmd(
    identifier: str = typer.Argument(help="Suggestion ID (or name for datasets)"),
    kind: str = typer.Option(..., "--kind", "-k", help="Kind: dataset, transform, or analysis"),
) -> None:
    """Accept a suggestion."""
    try:
        client = ShenasClient()
        if kind == "dataset":
            data = client._graphql(
                "mutation($name: String!) { acceptDatasetSuggestion(name: $name) }",
                {"name": identifier},
            )
            result = data.get("acceptDatasetSuggestion", {})
        elif kind == "transform":
            data = client._graphql(
                "mutation($id: Int!) { acceptTransformSuggestion(transformId: $id) }",
                {"id": int(identifier)},
            )
            result = data.get("acceptTransformSuggestion", {})
        elif kind == "analysis":
            data = client._graphql(
                "mutation($id: Int!) { acceptAnalysisSuggestion(hypothesisId: $id) }",
                {"id": int(identifier)},
            )
            result = data.get("acceptAnalysisSuggestion", {})
        else:
            console.print(f"[red]Unknown kind: {kind}. Use dataset, transform, or analysis.[/red]")
            raise typer.Exit(code=1)

        if result.get("ok"):
            console.print(f"[green]Accepted {kind} suggestion: {identifier}[/green]")
            if kind == "analysis" and result.get("question"):
                console.print(f"  Question: {result['question']}")
                console.print("  [dim]Run: shenasctl hypothesis ask '<question>'[/dim]")
        else:
            console.print(f"[red]{result.get('error', 'Failed')}[/red]")
            raise typer.Exit(code=1)

    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)


@app.command("dismiss")
def dismiss_cmd(
    identifier: str = typer.Argument(help="Suggestion ID (or name for datasets)"),
    kind: str = typer.Option(..., "--kind", "-k", help="Kind: dataset, transform, or analysis"),
) -> None:
    """Dismiss a suggestion."""
    try:
        client = ShenasClient()
        if kind == "dataset":
            data = client._graphql(
                "mutation($name: String!) { dismissDatasetSuggestion(name: $name) }",
                {"name": identifier},
            )
            result = data.get("dismissDatasetSuggestion", {})
        elif kind == "transform":
            data = client._graphql(
                "mutation($id: Int!) { dismissTransformSuggestion(transformId: $id) }",
                {"id": int(identifier)},
            )
            result = data.get("dismissTransformSuggestion", {})
        elif kind == "analysis":
            data = client._graphql(
                "mutation($id: Int!) { dismissAnalysisSuggestion(hypothesisId: $id) }",
                {"id": int(identifier)},
            )
            result = data.get("dismissAnalysisSuggestion", {})
        else:
            console.print(f"[red]Unknown kind: {kind}. Use dataset, transform, or analysis.[/red]")
            raise typer.Exit(code=1)

        if result.get("ok"):
            console.print(f"[yellow]Dismissed {kind} suggestion: {identifier}[/yellow]")
        else:
            console.print(f"[red]{result.get('error', 'Failed')}[/red]")
            raise typer.Exit(code=1)

    except ShenasServerError as exc:
        console.print(f"[red]{exc.detail}[/red]")
        raise typer.Exit(code=1)
