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
make install                        # install shenas + shenasrepoctl to ~/.local/bin/
make repository                     # start PEP 503 package server on :7290
make setup-hooks                    # install git pre-commit hook
make release-desktop                # tag a desktop release (version from commits)
moon run app:test                   # run tests for a single project
moon run :lint                      # run lint across all projects
moon run :test                      # run tests across all projects
moon run :coverage                  # run tests with coverage report
moon run :pyinstaller               # build standalone binaries (onedir) to dist/
moon run :build                     # build + sign all distributable wheels
moon run pipe-garmin:build           # build + sign a single pipe
moon run desktop:sidecars           # build PyInstaller sidecars for Tauri
moon run desktop:tauri              # build desktop app (builds sidecars first)
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
- **Lit + uPlot + Cytoscape + Vite** — frontend component stack
- **OpenTelemetry** — spans and logs exported to DuckDB, real-time SSE streaming

## Architecture

### Workspace packages

The monorepo is a uv workspace with 7 members, each a separate Python package:

- **`shenas-cli`** (`cli/`) — lightweight CLI client (httpx + typer + cryptography), no server deps
- **`shenas-app`** (`app/`) — FastAPI UI server, depends on shenas-cli
- **`shenas-scheduler`** (`scheduler/`) — background sync daemon sidecar, depends on shenas-cli
- **`shenas-repository`** (`repository/`) — PEP 503 package server + Ed25519 signing
- **`shenas-pipe-core`** (`plugins/pipes/core/`) — shared pipe utilities
- **`shenas-schema-core`** (`plugins/schemas/core/`) — shared schema utilities

Each has its own `pyproject.toml` with hatchling build, `VERSION` file, and `moon.yml` for task definitions. Cross-package imports (e.g. `cli` importing `repository.signing`, `app` importing `cli.db`) resolve via workspace editable installs with `dev-mode-dirs = [".."]` pointing to the repo root.

### Plugin discovery via entry points

Pipes register `[project.entry-points."shenas.pipes"]`, schemas register `shenas.schemas`, and components register `shenas.components`. The CLI and UI server discover them at runtime via `importlib.metadata.entry_points()`. Nothing is hardcoded to specific pipes or components.

All plugins are uv workspace members. `uv sync` installs everything for development. For production, users install plugins separately via `shenasctl pipe add`.

### Data flow: raw -> canonical

1. **Sync**: Pipe fetches from API, dlt loads into source-specific schema (`garmin.*`, `lunchmoney.*`)
2. **Transform**: Configurable SQL transforms stored in DuckDB (`shenas_system.transforms`): DELETE by source, INSERT into `metrics.*` (runs automatically after sync)
3. **Visualize**: Frontend queries `metrics.*` via Arrow IPC

### Shared core packages

- **`shenas-pipe-core`** (`plugins/pipes/core/`) — shared pipe utilities: `resolve_start_date`, `date_range`, `is_empty_response`, `create_pipe_app`, `run_sync`, `print_load_info`
- **`shenas-schema-core`** (`plugins/schemas/core/`) — shared schema utilities: `Field` (metadata dataclass), `generate_ddl`, `ensure_schema`, `table_metadata`, `schema_metadata`, `MetricProvider` protocol

Both are internal packages — hidden from `list`/`add`/`remove` commands. Pipes depend on `shenas-pipe-core`, schemas depend on `shenas-schema-core`.

### Canonical schema is dataclass-driven

Each schema package (e.g. `plugins/schemas/fitness/`) contains only a `metrics.py` with dataclasses. Fields use `Annotated[type, Field(...)]` for structured metadata (description, unit, value_range, interpretation). DDL is generated from these by `shenas-schema-core` — no hand-written SQL.

### Package distribution

All artifacts (pipes, components, schemas) are Python wheels served from a PEP 503 server (`repository/`). Wheels are Ed25519-signed (`.whl.sig` files alongside wheels in `packages/`). `shenas pipe add <name>` verifies the signature before installing.

### Component packaging workaround

`plugins/components/*/pyproject.build.toml` is renamed to `pyproject.toml` only during build (by the Makefile), then removed. This prevents uv from auto-discovering components as workspace members.

## Key conventions

- **Naming**: `shenas-pipe-*`, `shenas-component-*`, `shenas-schema-*`
- **Core packages**: `shenas-pipe-core`, `shenas-schema-core` (internal, not user-facing)
- **Versioning**: Each package has a `VERSION` file read by hatchling. `scripts/bump-version.py` auto-increments patch on every build.
- **Transforms are idempotent**: SQL transforms do DELETE WHERE source, then INSERT
- **Plugin kinds**: pipe, schema, component, ui, theme (all in `plugins/`)
- **Themes**: exclusive (only one enabled at a time), CSS custom properties pierce Shadow DOM
- **Python namespaces**: `shenas_pipes.*`, `shenas_schemas.*`, `shenas_components.*` (not `pipes.*` — conflicts with stdlib)
- **DuckDB schemas**: raw data in source-specific schemas (`garmin.*`, `lunchmoney.*`), canonical in `metrics.*`

## Modules

- `app/` — FastAPI UI server (shenas-app); discovers plugins via entry points, serves Arrow IPC
- `app/telemetry/` — OpenTelemetry exporters, DuckDB spans/logs, real-time SSE dispatcher
- `app/vendor/` — shared frontend deps (Lit, Arrow, uPlot, Cytoscape) built with Rollup
- `scheduler/` — background sync daemon sidecar (shenas-scheduler); polls server for due pipes
- `repository/` — PEP 503 Simple Repository API server + Ed25519 signing
- `scripts/` — build helpers (version bumping, pre-commit hook)
- `plugins/pipes/core/` — shared pipe utilities (shenas-pipe-core)
- `plugins/pipes/garmin/` — Garmin Connect dlt connector
- `plugins/pipes/lunchmoney/` — Lunch Money dlt connector
- `plugins/pipes/obsidian/` — Obsidian daily notes (frontmatter extraction)
- `plugins/pipes/gmail/` — Gmail (OAuth2, embedded client credentials)
- `plugins/pipes/duolingo/` — Duolingo (JWT browser auth)
- `plugins/pipes/spotify/` — Spotify (PKCE OAuth + history import)
- `plugins/schemas/core/` — shared schema utilities (shenas-schema-core)
- `plugins/schemas/fitness/` — canonical fitness metrics (HRV, sleep, vitals, body)
- `plugins/schemas/finance/` — canonical finance metrics (transactions, spending, budgets)
- `plugins/schemas/outcomes/` — canonical outcome metrics (mood, stress, productivity, exercise)
- `plugins/schemas/habits/` — canonical habits metrics (daily habits)
- `plugins/components/fitness-dashboard/` — Lit + uPlot fitness charts (built as wheel)
- `plugins/components/data-table/` — Lit data table with sorting/filtering/pagination (built as wheel)
- `plugins/themes/default/` — default light theme (CSS custom properties)
- `plugins/themes/dark/` — dark theme
- `plugins/ui/default/` — default UI shell (Lit SPA with tabs, command palette, data flow graph)

## Git workflow

- Never commit directly to main. Always create a feature branch first.
- Use conventional branch names: `feat/`, `fix/`, `refactor/`, `chore/`
- When done with changes, push the branch and open a PR via `gh pr create`.

## Hooks

Ruff check, ruff format, and ty check run automatically after every .py file edit via PostToolUse hook — no need to run manually.

Pre-commit hook runs `ruff check`, `ruff format --check`, and `ty check` before every commit. Install with `make setup-hooks`.
