# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Don't ask about doing 'cat', 'find', 'diff' or similar. Do not use emojis in code, docs, or commit messages.

When refactoring, unless told specifically so, don't bother with backward compatability.

## Commands

```bash
uv run shenasctl                       # CLI entry point
uv run shenasctl source garmin sync       # run pipe (must be installed first)
uv run ruff check .                 # lint
uv run ruff format .                # format
uv run ty check repository/ app/  # type check
uv run pytest                       # run tests
uv run cz commit                    # conventional commit
uv add <package>                    # add a dependency
uv sync                             # install dependencies
make install                        # install shenas + shenasctl to ~/.local/bin/
make setup-hooks                    # install git pre-commit hook
make release-desktop                # tag a desktop release (version from commits)
moon run app:test                   # run tests for a single project
moon run :lint                      # run lint across all projects
moon run :test                      # run tests across all projects
moon run :coverage                  # run tests with coverage report
moon run :pyinstaller               # build standalone binaries (onedir) to dist/
moon run :build                     # build all distributable wheels
moon run source-garmin:build           # build a single pipe
moon run desktop:sidecars           # build PyInstaller sidecars for Tauri
moon run desktop:tauri              # build desktop app (builds sidecars first)

# JavaScript / TypeScript
npm install                                                      # root: install eslint + prettier + typescript
npm run lint                                                     # eslint all TS
npm run format                                                   # prettier write
npm run format:check                                             # prettier check
npx tsc --noEmit -p plugins/frontends/default/tsconfig.json      # type check one package
cd app/vendor && npm test                                        # vendor tests
cd plugins/dashboards/data-table && npm run coverage             # coverage one package
```

## Stack

- **dlt** — data ingestion/pipeline framework (`@dlt.source`, `@dlt.resource`, incremental cursors)
- **DuckDB** — local destination at `./data/shenas.duckdb` (also available via MCP server `duckdb`)
- **uv** — package manager (do not use pip directly); workspace with glob-based members (app, shenasctl, scheduler, server/api, plugins/\*)
- **moon** — monorepo task runner; config in `.moon/`, per-project `moon.yml`
- **typer** — CLI framework; **rich** — terminal formatting
- **FastAPI** — app server + web API
- **pyarrow** — Arrow IPC streaming for app queries
- **cryptography** — Ed25519 package signing
- **hatchling** — wheel builder for pipes, schemas, and components
- **Lit + uPlot + Cytoscape + Vite** — frontend component stack
- **OpenTelemetry** — spans and logs exported to DuckDB, real-time SSE streaming

## Architecture

### Workspace packages

The monorepo is a uv workspace with glob-based members, each a separate Python package:

- **`shenas-cli`** (`shenasctl/`) — lightweight CLI client (httpx + typer + cryptography), no server deps
- **`shenas-app`** (`app/`) — FastAPI UI server, depends on shenas-cli
- **`shenas-scheduler`** (`scheduler/`) — background sync daemon sidecar, depends on shenas-cli
- **`shenas-plugin-core`** (`plugins/core/`) — shared plugin utilities
- **`shenas-source-core`** (`plugins/sources/core/`) — shared pipe utilities
- **`shenas-dataset-core`** (`plugins/datasets/core/`) — shared schema utilities

Sources, datasets, dashboards, UIs, and themes under `plugins/` are auto-discovered via glob patterns. Each has its own `pyproject.toml` with hatchling build, `VERSION` file, and `moon.yml` for task definitions. Cross-package imports resolve via workspace editable installs with `dev-mode-dirs = [".."]` pointing to the repo root.

### Plugin discovery via entry points

Sources register `[project.entry-points."shenas.sources"]`, datasets register `shenas.datasets`, dashboards register `shenas.dashboards`, frontends register `shenas.frontends`, themes register `shenas.themes`. The CLI and UI server discover them at runtime via `importlib.metadata.entry_points()`. Nothing is hardcoded to specific sources or dashboards.

All plugins are uv workspace members. `uv sync` installs everything for development. For production, users install plugins separately via `shenasctl source add`.

### Raw table semantics: `__kind__`

Every raw source-table dataclass declares a `__kind__: ClassVar[TableKind]` (defined in `shenas_plugins.core.field`):

- **`event`** — discrete, immutable occurrence with its own native timestamp (activity, transaction, email). PK is the natural id; dlt strategy is merge on id.
- **`snapshot`** — current self-state with no temporal axis and nothing else joins to it (profile, current zones, current top tracks). dlt strategy is replace.
- **`dimension`** — reference / lookup data that other tables join against (calendars, labels, categories, tags, assets, plaid accounts, color palette). Same write semantics as snapshot (replace) but flagged separately so dashboards know which tables are joinable lookups vs leaf state.
- **`aggregate`** — per-window summary that can be re-emitted as new data arrives (daily HRV, daily sleep, daily XP). dlt strategy is merge on `(window_key, ...)`.
- **`counter`** — monotonically growing scalar where deltas matter (gear distance). dlt strategy is merge on entity id.

### Data flow: raw -> canonical

1. **Sync**: Source fetches from API, dlt loads into source-specific schema (`garmin.*`, `lunchmoney.*`, `strava.*`, ...)
2. **Transform**: Configurable SQL transforms stored in DuckDB (`shenas_system.transforms`): DELETE by source, INSERT into `metrics.*` (runs automatically after sync)
3. **Visualize**: Frontend queries `metrics.*` via Arrow IPC

### Shared core packages

- **`shenas-source-core`** (`plugins/sources/core/`) — shared source utilities: `resolve_start_date`, `date_range`, `is_empty_response`, `create_pipe_app`, `run_sync`, `print_load_info`
- **`shenas-dataset-core`** (`plugins/datasets/core/`) — shared dataset utilities: `Field` (metadata dataclass), `generate_ddl`, `ensure_schema`, `table_metadata`, `schema_metadata`, `MetricProvider` protocol

Both are internal packages — hidden from `list`/`add`/`remove` commands. Sources depend on `shenas-source-core`, datasets depend on `shenas-dataset-core`.

### Canonical dataset is dataclass-driven

Each dataset package (e.g. `plugins/datasets/fitness/`) contains only a `metrics.py` with dataclasses. Fields use `Annotated[type, Field(...)]` for structured metadata (description, unit, value_range, interpretation). DDL is generated from these by `shenas-dataset-core` — no hand-written SQL.

### Package distribution

All artifacts (sources, dashboards, datasets, frontends, themes) are Python wheels distributed as GitHub releases. Wheels are Ed25519-signed in CI. `shenas source add <name>` verifies the signature before installing.

### Dashboard packaging workaround

`plugins/dashboards/*/pyproject.build.toml` is renamed to `pyproject.toml` only during build (by the Makefile), then removed. This prevents uv from auto-discovering dashboards as workspace members.

## Key conventions

- **Naming**: `shenas-source-*`, `shenas-dashboard-*`, `shenas-dataset-*`
- **Core packages**: `shenas-source-core`, `shenas-dataset-core` (internal, not user-facing)
- **Versioning**: Each package has a `VERSION` file read by hatchling. `scripts/bump-version.py` auto-increments patch on every build.
- **Transforms are idempotent**: SQL transforms do DELETE WHERE source, then INSERT
- **Plugin kinds**: source, dataset, dashboard, frontend, theme (all in `plugins/`)
- **Themes**: exclusive (only one enabled at a time), CSS custom properties pierce Shadow DOM
- **Python namespaces**: `shenas_sources.*`, `shenas_datasets.*`, `shenas_dashboards.*` (not `pipes.*` — conflicts with stdlib)
- **DuckDB schemas**: raw data in source-specific schemas (`garmin.*`, `lunchmoney.*`, `strava.*`, ...), canonical in `metrics.*`
- **Raw table semantics**: every table dataclass declares a `__kind__` ClassVar (`event` | `snapshot` | `dimension` | `aggregate` | `counter`) — see "Raw table semantics" above

## Modules

- `app/` — FastAPI UI server (shenas-app); discovers plugins via entry points, serves Arrow IPC
- `app/telemetry/` — OpenTelemetry exporters, DuckDB spans/logs, real-time SSE dispatcher
- `app/fl/` — Flower FL client, PyTorch training, inference engine, model plugin registry
- `app/desktop/` — Tauri v2 desktop app with bundled PyInstaller sidecars
- `app/mobile/` — Tauri v2 mobile app (Rust core: axum + DuckDB, no Python)
- `app/vendor/` — shared frontend deps (Lit, Arrow, uPlot, Cytoscape) built with Rollup
- `shenasctl/` — lightweight CLI client (shenas-cli); httpx + typer + cryptography
- `scheduler/` — background sync daemon sidecar (shenas-scheduler); polls server for due pipes
- `server/fl/` — federated learning coordinator (Flower server + REST API); runs in its own venv
- `scripts/` — build helpers (version bumping, pre-commit hook)
- `plugins/core/` — shared plugin utilities (shenas-plugin-core)
- `plugins/sources/core/` — shared source utilities (shenas-source-core)
- `plugins/sources/garmin/` — Garmin Connect (activities, daily stats, sleep, HRV, SpO2, body composition)
- `plugins/sources/gcalendar/` — Google Calendar (events with attendees + colors palette)
- `plugins/sources/gtakeout/` — Google Takeout import (photos, location, YouTube history)
- `plugins/sources/lunchmoney/` — Lunch Money (transactions, transaction_tags, categories, budgets, recurring, assets, plaid, user, crypto)
- `plugins/sources/obsidian/` — Obsidian daily notes (frontmatter extraction)
- `plugins/sources/gmail/` — Gmail (messages, labels, profile, filters, vacation, send_as)
- `plugins/sources/duolingo/` — Duolingo (XP, courses, profile, achievements, league, friends)
- `plugins/sources/spotify/` — Spotify (recently played, top tracks/artists for all 3 time ranges, saved tracks/albums/shows/episodes, playlists, followed artists, audio_features, user_profile)
- `plugins/sources/strava/` — Strava (activities with detail, laps, kudos, comments, athlete, athlete_stats, athlete_zones, gear)
- `plugins/datasets/core/` — shared schema utilities (shenas-dataset-core)
- `plugins/datasets/fitness/` — canonical fitness metrics (HRV, sleep, vitals, body)
- `plugins/datasets/finance/` — canonical finance metrics (transactions, spending, budgets)
- `plugins/datasets/events/` — unified event timeline
- `plugins/datasets/outcomes/` — canonical outcome metrics (mood, stress, productivity, exercise)
- `plugins/datasets/habits/` — canonical habits metrics (daily habits)
- `plugins/dashboards/fitness-dashboard/` — Lit + uPlot fitness charts (built as wheel)
- `plugins/dashboards/data-table/` — Lit data table with sorting/filtering/pagination (built as wheel)
- `plugins/themes/default/` — default light theme (CSS custom properties)
- `plugins/themes/dark/` — dark theme
- `plugins/frontends/default/` — default UI shell (Lit SPA with tabs, command palette, data flow graph)

## Git workflow

- Never commit directly to main. Always create a feature branch first.
- Use conventional branch names: `feat/`, `fix/`, `refactor/`, `chore/`
- When done with changes, push the branch and open a PR via `gh pr create`.

## Hooks

Ruff check, ruff format, and ty check run automatically after every .py file edit via PostToolUse hook — no need to run manually.

Pre-commit hook runs `ruff check`, `ruff format --check`, and `ty check` before every commit. Install with `make setup-hooks`.
