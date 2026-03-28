# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Don't ask about doing 'cat', 'find', 'diff' or similar. Do not use emojis in code, docs, or commit messages.

## Commands

```bash
uv run shenasctl                       # CLI entry point
uv run shenasctl pipe garmin sync       # run pipe (must be installed first)
uv run ruff check .                 # lint
uv run ruff format .                # format
uv run ty check repository/ app/  # type check
uv run pytest                       # run tests
uv run cz commit                    # conventional commit
uv add <package>                    # add a dependency
uv sync                             # install dependencies
make dev-uninstall                  # uninstall all shenas-* packages
make build-pipes                    # build all pipe wheels (auto-bumps VERSION)
make build-schemas                  # build all schema wheels
make build-components               # build all component wheels
make repository              # start PEP 503 package server on :7290
make coverage                       # run tests with coverage report
make setup-hooks                    # install git pre-commit hook
moon run cli:test                   # run tests for a single project
moon run :lint                      # run lint across all projects
moon run :test                      # run tests across all projects
shenasrepoctl sign-all packages/   # sign all unsigned wheels
shenasrepoctl vendor garmin        # vendor a pipe and its deps
```

## Stack

- **dlt** — data ingestion/pipeline framework (`@dlt.source`, `@dlt.resource`, incremental cursors)
- **DuckDB** — local destination at `./data/shenas.duckdb` (also available via MCP server `duckdb`)
- **uv** — package manager (do not use pip directly); workspace with 5 members (cli, app, repository, pipes/core, schemas/core)
- **moon** — monorepo task runner; config in `.moon/`, per-project `moon.yml`
- **typer** — CLI framework; **rich** — terminal formatting
- **FastAPI** — repository server + app server
- **pyarrow** — Arrow IPC streaming for app queries
- **cryptography** — Ed25519 package signing
- **hatchling** — wheel builder for pipes, schemas, and components
- **Lit + uPlot + Vite** — frontend component stack

## Architecture

### Workspace packages

The monorepo is a uv workspace with 5 members, each a separate Python package:

- **`shenas-cli`** (`cli/`) — CLI entry point, depends on shenas-app + shenas-repository
- **`shenas-app`** (`app/`) — FastAPI UI server (renamed from local_frontend)
- **`shenas-repository`** (`repository/`) — PEP 503 package server + Ed25519 signing
- **`shenas-pipe-core`** (`pipes/core/`) — shared pipe utilities
- **`shenas-schema-core`** (`schemas/core/`) — shared schema utilities

Each has its own `pyproject.toml` with hatchling build, `VERSION` file, and `moon.yml` for task definitions. Cross-package imports (e.g. `cli` importing `repository.signing`, `app` importing `cli.db`) resolve via workspace editable installs with `dev-mode-dirs = [".."]` pointing to the repo root.

### Plugin discovery via entry points

Pipes register `[project.entry-points."shenas.pipes"]`, schemas register `shenas.schemas`, and components register `shenas.components`. The CLI and UI server discover them at runtime via `importlib.metadata.entry_points()`. Nothing is hardcoded to specific pipes or components.

All plugins are uv workspace members. `uv sync` installs everything for development. For production, users install plugins separately via `shenasctl pipe add`.

### Data flow: raw -> canonical

1. **Sync**: Pipe fetches from API, dlt loads into source-specific schema (`garmin.*`, `lunchmoney.*`)
2. **Transform**: Pipe's `MetricProviderBase._upsert()` runs SQL: DELETE by source, INSERT into `metrics.*` (runs automatically after sync)
3. **Visualize**: Frontend queries `metrics.*` via Arrow IPC

### Shared core packages

- **`shenas-pipe-core`** (`pipes/core/`) — shared pipe utilities: `resolve_start_date`, `date_range`, `is_empty_response`, `MetricProviderBase` (with `_upsert`), `create_pipe_app`, `run_sync`, `print_load_info`
- **`shenas-schema-core`** (`schemas/core/`) — shared schema utilities: `Field` (metadata dataclass), `generate_ddl`, `ensure_schema`, `table_metadata`, `schema_metadata`, `MetricProvider` protocol

Both are internal packages — hidden from `list`/`add`/`remove` commands. Pipes depend on `shenas-pipe-core`, schemas depend on `shenas-schema-core`.

### Canonical schema is dataclass-driven

Each schema package (e.g. `schemas/fitness/`) contains only a `metrics.py` with dataclasses. Fields use `Annotated[type, Field(...)]` for structured metadata (description, unit, value_range, interpretation). DDL is generated from these by `shenas-schema-core` — no hand-written SQL.

### Package distribution

All artifacts (pipes, components, schemas) are Python wheels served from a PEP 503 server (`repository/`). Wheels are Ed25519-signed (`.whl.sig` files alongside wheels in `packages/`). `shenas pipe add <name>` verifies the signature before installing.

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

- `cli/` — `shenas` CLI (shenas-cli); subcommands under `cli/commands/`
- `pipes/core/` — shared pipe utilities (shenas-pipe-core)
- `pipes/garmin/` — Garmin Connect dlt connector
- `pipes/lunchmoney/` — Lunch Money dlt connector
- `pipes/obsidian/` — Obsidian daily notes (frontmatter extraction)
- `pipes/gmail/` — Gmail (OAuth2, embedded client credentials)
- `schemas/core/` — shared schema utilities (shenas-schema-core)
- `schemas/fitness/` — canonical fitness metrics (HRV, sleep, vitals, body)
- `schemas/finance/` — canonical finance metrics (transactions, spending, budgets)
- `schemas/outcomes/` — canonical outcome metrics (mood, stress, productivity, exercise, etc.)
- `repository/` — PEP 503 Simple Repository API server + Ed25519 signing
- `app/` — FastAPI UI server (shenas-app); discovers components via entry points, serves Arrow IPC
- `components/fitness-dashboard/` — Lit + uPlot fitness charts (built as wheel)
- `components/data-table/` — Lit data table with sorting/filtering/pagination (built as wheel)
- `scripts/` — build helpers (version bumping, pre-commit hook)
- `tests/` — tests for repository, app, CLI, signing

## Git workflow

- Never commit directly to main. Always create a feature branch first.
- Use conventional branch names: `feat/`, `fix/`, `refactor/`, `chore/`
- When done with changes, push the branch and open a PR via `gh pr create`.

## Hooks

Ruff check, ruff format, and ty check run automatically after every .py file edit via PostToolUse hook — no need to run manually.

Pre-commit hook runs `ruff check`, `ruff format --check`, and `ty check` before every commit. Install with `make setup-hooks`.
