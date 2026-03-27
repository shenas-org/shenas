# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Don't ask about doing 'cat', 'find', 'diff' or similar. Do not use emojis in code, docs, or commit messages.

## Commands

```bash
uv run shenas                       # CLI entry point
uv run shenas pipe garmin sync       # run pipe (must be installed first)
uv run ruff check .                 # lint
uv run ruff format .                # format
uv run ty check cli/ registry/ repository_server/ local_frontend/  # type check
uv run pytest                       # run tests
uv run cz commit                    # conventional commit
uv add <package>                    # add a dependency
uv sync                             # install dependencies
make dev-install                    # editable install all local packages
make dev-uninstall                  # uninstall all shenas-* packages
make build-pipes                    # build all pipe wheels (auto-bumps VERSION)
make build-schemas                  # build all schema wheels
make build-components               # build all component wheels
make repository_server              # start PEP 503 package server on :8080
make lint                           # run ruff + ty
make test                           # run pytest
make coverage                       # run tests with coverage report
make setup-hooks                    # install git pre-commit hook
```

## Stack

- **dlt** — data ingestion/pipeline framework (`@dlt.source`, `@dlt.resource`, incremental cursors)
- **DuckDB** — local destination at `./data/shenas.duckdb` (also available via MCP server `duckdb`)
- **uv** — package manager (do not use pip directly)
- **typer** — CLI framework; **rich** — terminal formatting
- **FastAPI** — repository server + local frontend
- **pyarrow** — Arrow IPC streaming for frontend queries
- **cryptography** — Ed25519 package signing
- **hatchling** — wheel builder for pipes, schemas, and components
- **Lit + uPlot + Vite** — frontend component stack

## Architecture

### Plugin discovery via entry points

Pipes register `[project.entry-points."shenas.pipes"]`, schemas register `shenas.schemas`, and components register `shenas.components`. The CLI and UI server discover them at runtime via `importlib.metadata.entry_points()`. Nothing is hardcoded to specific pipes or components.

Pipes and schemas must be installed to be discovered. For development, use `make dev-install` for editable installs of all local packages.

### Data flow: raw -> canonical

1. **Sync**: Pipe fetches from API, dlt loads into source-specific schema (`garmin.*`, `lunchmoney.*`)
2. **Transform**: Pipe's `MetricProviderBase._upsert()` runs SQL: DELETE by source, INSERT into `metrics.*` (runs automatically after sync)
3. **Visualize**: Frontend queries `metrics.*` via Arrow IPC

### Shared core packages

- **`shenas-pipe-core`** (`pipes/core/`) — shared pipe utilities: `resolve_start_date`, `date_range`, `is_empty_response`, `MetricProviderBase` (with `_upsert`), `create_pipe_app`, `run_sync`, `print_load_info`
- **`shenas-schema-core`** (`schemas/core/`) — shared schema utilities: `Field` (metadata dataclass), `generate_ddl`, `ensure_schema`, `table_metadata`, `schema_metadata`, `MetricProvider` protocol

Both are internal packages — hidden from `list`/`add`/`remove` commands. Pipes depend on `shenas-pipe-core`, schemas depend on `shenas-schema-core`.

### Canonical schema is dataclass-driven

Each schema package (e.g. `schemas/fitness_tracker/`) contains only a `metrics.py` with dataclasses. Fields use `Annotated[type, Field(...)]` for structured metadata (description, unit, value_range, interpretation). DDL is generated from these by `shenas-schema-core` — no hand-written SQL.

### Package distribution

All artifacts (pipes, components, schemas) are Python wheels served from a PEP 503 server (`repository_server/`). Wheels are Ed25519-signed (`.whl.sig` files alongside wheels in `packages/`). `shenas pipe add <name>` verifies the signature before installing.

### Component packaging workaround

`components/*/pyproject.build.toml` is renamed to `pyproject.toml` only during build (by the Makefile), then removed. This prevents uv from auto-discovering components as workspace members. Same for non-workspace schemas (e.g. `schemas/finance/`).

## Key conventions

- **Naming**: `shenas-pipe-*`, `shenas-component-*`, `shenas-schema-*`
- **Core packages**: `shenas-pipe-core`, `shenas-schema-core` (internal, not user-facing)
- **Versioning**: Each package has a `VERSION` file read by hatchling. `scripts/bump-version.py` auto-increments patch on every build.
- **Transforms are idempotent**: `MetricProviderBase._upsert()` does DELETE WHERE source, then INSERT
- **Python namespaces**: `shenas_pipes.*`, `shenas_schemas.*`, `shenas_components.*` (not `pipes.*` — conflicts with stdlib)
- **DuckDB schemas**: raw data in source-specific schemas (`garmin.*`, `lunchmoney.*`), canonical in `metrics.*`

## Modules

- `cli/` — `shenas` CLI; subcommands under `cli/commands/`
- `pipes/core/` — shared pipe utilities (shenas-pipe-core)
- `pipes/garmin/` — Garmin Connect dlt connector
- `pipes/lunchmoney/` — Lunch Money dlt connector
- `schemas/core/` — shared schema utilities (shenas-schema-core)
- `schemas/fitness_tracker/` — canonical fitness metrics (HRV, sleep, vitals, body)
- `schemas/finance/` — canonical finance metrics (transactions, spending, budgets)
- `registry/` — Ed25519 signing/verification
- `repository_server/` — PEP 503 Simple Repository API server
- `local_frontend/` — FastAPI UI server; discovers components via entry points, serves Arrow IPC
- `components/` — web component source (Lit/Vite); built into Python wheels
- `scripts/` — build helpers (version bumping, pre-commit hook)
- `tests/` — tests for repository_server, local_frontend, CLI, signing

## Hooks

Ruff check, ruff format, and ty check run automatically after every .py file edit via PostToolUse hook — no need to run manually.

Pre-commit hook runs `ruff check`, `ruff format --check`, and `ty check` before every commit. Install with `make setup-hooks`.
