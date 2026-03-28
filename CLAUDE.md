# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Don't ask about doing 'cat', 'find', 'diff' or similar. Do not use emojis in code, docs, or commit messages.

## Commands

```bash
uv run shenas                       # CLI entry point
uv run shenas --dev pipe garmin sync # run pipe from local source (not installed)
uv run ruff check .                 # lint
uv run ruff format .                # format
uv run cz commit                    # conventional commit
uv add <package>                    # add a dependency
uv sync                             # install dependencies
make build-pipes                    # build all pipe wheels (auto-bumps VERSION)
make build-components               # build all component wheels
make repository_server              # start PEP 503 package server on :8080
```

## Stack

- **dlt** — data ingestion/pipeline framework (`@dlt.source`, `@dlt.resource`, incremental cursors)
- **DuckDB** — local destination at `./data/local.duckdb` (also available via MCP server `duckdb`)
- **uv** — package manager (do not use pip directly)
- **typer** — CLI framework; **rich** — terminal formatting
- **FastAPI** — repository server + local frontend
- **pyarrow** — Arrow IPC streaming for frontend queries
- **cryptography** — Ed25519 package signing
- **hatchling** — wheel builder for pipes and components
- **Lit + uPlot + Vite** — frontend component stack

## Architecture

### Plugin discovery via entry points

Pipes register `[project.entry-points."shenas.pipes"]` and components register `[project.entry-points."shenas.components"]`. The CLI and UI server discover them at runtime via `importlib.metadata.entry_points()`. Nothing is hardcoded to specific pipes or components.

`--dev` mode bypasses entry points and loads pipes directly from `pipes/*/src/` using `importlib.util.spec_from_file_location`. This happens at import time in `cli/commands/pipe.py` (checks `"--dev" in sys.argv`), not in the typer callback.

### Data flow: raw -> canonical

1. **Sync**: Pipe fetches from API, dlt loads into source-specific schema (`garmin.*`)
2. **Transform**: Pipe's `MetricProvider.transform()` runs SQL: DELETE by source, INSERT into `metrics.*`
3. **Visualize**: Frontend queries `metrics.*` via Arrow IPC

### Canonical schema is dataclass-driven

`schema/metrics.py` defines dataclasses with `__table__`, `__pk__`, and `Annotated` type hints. `schema/ddl.py` generates DDL from these — no hand-written SQL. Adding a column means editing the dataclass.

### Package distribution

All artifacts (pipes, components, schemas) are Python wheels served from a PEP 503 server (`repository_server/`). Wheels are Ed25519-signed (`.whl.sig` files alongside wheels in `packages/`). `shenas install pipe <name>` verifies the signature before installing via `uv pip install --index-url`.

### Component packaging workaround

`frontend_components/*/pyproject.build.toml` is renamed to `pyproject.toml` only during build (by the Makefile), then removed. This prevents uv from auto-discovering components as workspace members.

## Key conventions

- **Naming**: `shenas-pipe-*`, `shenas-component-*`, `shenas-schema-*`
- **Versioning**: Each package has a `VERSION` file read by hatchling. `scripts/bump-version.py` auto-increments patch on every build.
- **Transforms are idempotent**: DELETE WHERE source = X, then INSERT
- **Python namespace**: `shenas_pipes.*` (not `pipes.*` — conflicts with stdlib)
- **DuckDB schemas**: raw data in `garmin.*`, canonical in `metrics.*`

## Modules

- `cli/` — `shenas` CLI; subcommands under `cli/commands/`
- `pipes/` — dlt connectors as standalone packages (e.g. `pipes/garmin/`)
- `schema/` — canonical metric types, DDL generation, MetricProvider protocol
- `registry/` — Ed25519 signing/verification
- `repository_server/` — PEP 503 Simple Repository API server
- `local_frontend/` — FastAPI UI server; discovers components via entry points, serves Arrow IPC
- `frontend_components/` — web component source (Lit/Vite); built into Python wheels
- `scripts/` — build helpers (version bumping)

## Hooks

Ruff check and format run automatically after every file edit via PostToolUse hook — no need to run manually.
