# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Don't ask about doing 'cat', 'find', 'diff' or similar. Do not use emojis in code, docs, or commit messages.

## Commands

```bash
uv run shenas                       # CLI entry point
uv run shenas pipe garmin sync       # run pipe (must be installed first)
uv run ruff check .                 # lint
uv run ruff format .                # format
uv run cz commit                    # conventional commit
uv add <package>                    # add a dependency
uv sync                             # install dependencies
make build-pipes                    # build all pipe wheels (auto-bumps VERSION)
make build-schemas                  # build all schema wheels
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

Pipes and schemas must be installed to be discovered. For development, install them as editable workspace members with `uv pip install -e pipes/garmin` or build and install the wheel.

### Data flow: raw -> canonical

1. **Sync**: Pipe fetches from API, dlt loads into source-specific schema (`garmin.*`)
2. **Transform**: Pipe's `MetricProvider.transform()` runs SQL: DELETE by source, INSERT into `metrics.*`
3. **Visualize**: Frontend queries `metrics.*` via Arrow IPC

### Canonical schema is dataclass-driven

`schemas/fitness_tracker/shenas_schemas/fitness_tracker/metrics.py` defines dataclasses with `__table__`, `__pk__`, and `Annotated` type hints. DDL is generated from these — no hand-written SQL. Adding a column means editing the dataclass. The schema is a standalone package (`shenas-schema-fitness-tracker`) that pipes and components depend on.

### Package distribution

All artifacts (pipes, components, schemas) are Python wheels served from a PEP 503 server (`repository_server/`). Wheels are Ed25519-signed (`.whl.sig` files alongside wheels in `packages/`). `shenas install pipe <name>` verifies the signature before installing via `uv pip install --index-url`.

### Component packaging workaround

`frontend_components/*/pyproject.build.toml` is renamed to `pyproject.toml` only during build (by the Makefile), then removed. This prevents uv from auto-discovering components as workspace members.

## Key conventions

- **Naming**: `shenas-pipe-*`, `shenas-component-*`, `shenas-schema-*`
- **Versioning**: Each package has a `VERSION` file read by hatchling. `scripts/bump-version.py` auto-increments patch on every build.
- **Transforms are idempotent**: DELETE WHERE source = X, then INSERT
- **Python namespaces**: `shenas_pipes.*`, `shenas_schemas.*`, `shenas_components.*` (not `pipes.*` — conflicts with stdlib)
- **DuckDB schemas**: raw data in `garmin.*`, canonical in `metrics.*`

## Modules

- `cli/` — `shenas` CLI; subcommands under `cli/commands/`
- `pipes/` — dlt connectors as standalone packages (e.g. `pipes/garmin/`)
- `schemas/` — canonical schemas as standalone packages (e.g. `schemas/fitness_tracker/`)
- `registry/` — Ed25519 signing/verification
- `repository_server/` — PEP 503 Simple Repository API server
- `local_frontend/` — FastAPI UI server; discovers components via entry points, serves Arrow IPC
- `frontend_components/` — web component source (Lit/Vite); built into Python wheels
- `scripts/` — build helpers (version bumping)

## Hooks

Ruff check, ruff format, and ty check run automatically after every .py file edit via PostToolUse hook — no need to run manually.
