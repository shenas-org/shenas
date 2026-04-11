# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Don't ask about doing 'cat', 'find', 'diff' or similar. Do not use emojis in code, docs, or commit messages.

When refactoring, unless told specifically so, don't bother with backward compatability.

Prefer object-oriented code when idiomatic -- classes with methods over loose functions and dicts.

## Guiding documents

The `prompts/` folder contains documents that guide Claude, MCPs, and other LLMs when generating user-facing content:

- `prompts/TONE_OF_VOICE.md` -- how shenas talks to users (UI text, errors, changelogs, docs)
- `prompts/DESIGN.md` -- visual design system (colors, typography, layout, components)
- `prompts/DISCOURSE.md` -- Discourse community forum theming

Consult these when writing UI copy, error messages, documentation, or frontend components.

## Commands

```bash
# Setup
uv sync                                # install dependencies
make app-install                       # install shenas + shenasctl to ~/.local/bin/
make hooks-setup                       # install git pre-commit hook

# Run
shenasctl                              # CLI entry point
shenasctl source garmin sync           # run pipe (must be installed first)

# Lint and test (same commands as CI)
moon run :lint                         # all lints: python + JS lint, format, typecheck
moon run :test                         # all tests
make coverage                          # tests with coverage report
moon run :python-lint                  # ruff check
moon run :python-format-check          # ruff format --check
moon run :python-type-check            # ty check
moon run :python-test                  # pytest
moon run :js-lint                      # eslint
moon run :js-format-check              # prettier --check
moon run :js-type-check                # tsc --noEmit (all TS packages)
moon run app:python-test               # tests for a single project

# Build
moon run :build                        # build all distributable wheels
moon run source-garmin:build           # build a single package
make pyinstaller                       # build standalone binaries (onedir) to dist/
moon run desktop:sidecars              # build PyInstaller sidecars for Tauri
moon run desktop:tauri                 # build desktop app (builds sidecars first)

# Other
uv run cz commit                       # conventional commit
uv add <package>                       # add a dependency
make desktop-release                   # tag a desktop release (version from commits)
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

### Common Table ABC: SourceTable + MetricTable

Every plugin-defined DuckDB-persisted dataclass inherits from a slim common `Table` ABC at `plugins/core/shenas_plugins/core/table.py`. The metadata ClassVars are prefixed `table_*` (`table_name`, `table_display_name`, `table_pk`, `table_description`) so they never collide with row-level columns called `name`, `description`, etc. The base auto-applies `@dataclass` via `__init_subclass__` and validates the required ClassVars at class-definition time.

Three layers:

- **`Table`** (in `shenas-plugin-core`) — slim common base: `table_name`, `table_display_name`, `table_pk`, `table_description`. Auto-`@dataclass`.
- **`SourceTable(Table)`** (in `shenas-source-core`) — adds `cursor_column`, `extract()`, `to_resource()`, `write_disposition()`, `to_dlt_columns()`, observed_at injection. The 7 kind base classes (`EventTable`, `IntervalTable`, `SnapshotTable`, `DimensionTable`, `AggregateTable`, `CounterTable`, `M2MTable`) inherit from `SourceTable`. The kind is encoded in the inheritance chain — there's no `kind` ClassVar; check kinds via `issubclass(MyTable, IntervalTable)`.
- **`MetricTable(Table)`** (in `shenas-dataset-core`) — adds `to_ddl(schema="metrics")`. Used by every dataset plugin's metric tables. Future home of per-table `transform(cls, con)` classmethods (Source -> Metric and Metric -> Metric).

Other persisted dataclasses also inherit from `Table` directly: `Plugin._Table` (the installed-plugins registry), `Transform._Table` (user-supplied SQL transforms), `Workspace._Table`, `Hotkey._Table`, and `SourceConfig` / `SourceAuth` (per-pipe credential / config storage). `SourceConfig` and `SourceAuth` defer validation via their own `__init_subclass__` because `table_name` is set lazily by `Source.__init_subclass__`; they call `cls._finalize()` after assigning `table_name` to apply the auto-`@dataclass` and run validation.

`TableStore` (formerly `DataclassStore`, in `shenas-plugin-core`) is the thin single-row CRUD wrapper used by `Source._config_store` and `Source._auth_store`. It accepts any `Table` subclass.

### Raw table semantics: kind base classes

Every raw source table is a subclass of one of six kind base classes in `shenas_sources.core.table`. The kind is encoded in the inheritance chain (no magic strings) and determines the dlt write_disposition automatically:

- **`EventTable`** — discrete, immutable occurrence at a single point in time. Declares `time_at` (the timestamp column); if omitted, an `observed_at` column is auto-injected from sync time. PK is the natural id. dlt strategy is merge on id.
- **`IntervalTable`** — discrete occurrence with both a start and an end timestamp. Declares `time_start` and `time_end` (both required). PK is the natural id. dlt strategy is merge on id. Examples: a calendar event, a workout, a sleep session.
- **`SnapshotTable`** — current self-state with no temporal axis. Loaded as **SCD2** (hash-then-version) so every observed change becomes a new row with disjoint `_dlt_valid_from` / `_dlt_valid_to` ranges. Nothing else joins to it. dlt strategy is `merge` with `strategy="scd2"`.
- **`DimensionTable`** — reference / lookup data that other tables join against. Same SCD2 loader as snapshot but flagged separately so dashboards know which tables are joinable lookups. Historical joins return the value that was true at the time, not the current value. dlt strategy is `merge` with `strategy="scd2"`.
- **`AggregateTable`** — per-window summary that can be re-emitted as new data arrives. PK includes the window key (date/hour) and that same key is `time_at`. dlt strategy is merge on (window_key, ...).
- **`CounterTable`** — monotonically growing scalar where deltas matter. Loaded as append-with-`observed_at` so consumers can compute deltas across observations. Declares `counter_columns`. dlt strategy is `append`.
- **`M2MTable`** — many-to-many bridge / link table joining two entities. Composite PK is the two foreign keys; rows typically have NO additional value columns (denormalized attributes belong on the entity dimensions, joined as needed). Loaded as **SCD2** so when a link disappears between syncs (the user removes a tag, unfollows an artist, etc.) the row's `_dlt_valid_to` is closed instead of leaving it alive forever. Examples: `lunchmoney.transaction_tags`, `spotify.followed_artists`, `strava.kudos`, `gcalendar.event_attendees`.

Each `Table` subclass owns its schema fields, metadata (`name`, `display_name`, `description`, `pk`, kind-specific attrs), and the extraction logic in one place via a `extract(client, **context)` classmethod. The class becomes a dlt resource via `cls.to_resource(client, **context)`. A `Source` then just enumerates its `Table` subclasses:

```python
class LunchMoneySource(Source):
    def resources(self, client):
        from shenas_sources.lunchmoney.tables import TABLES
        return [t.to_resource(client, start_date="90 days ago") for t in TABLES]
```

All sources use the Table ABC pattern.

### AS-OF macros for SCD2 tables

After every sync, `Source.sync()` calls `apply_as_of_macros(con, schema)` from `shenas_sources.core.as_of`, which discovers any table in the source's schema with both `_dlt_valid_from` and `_dlt_valid_to` columns and creates a DuckDB macro per table:

```sql
CREATE OR REPLACE MACRO <schema>.<table>_as_of(ts) AS TABLE
  SELECT * FROM <schema>.<table>
  WHERE _dlt_valid_from <= ts
    AND (_dlt_valid_to IS NULL OR _dlt_valid_to > ts);
```

Example: `SELECT * FROM gcalendar.calendars_as_of('2026-01-15')` returns the calendar names that were valid on 2026-01-15 instead of the current ones. Discovery is column-shape-based, so any new SCD2 table picked up by dlt automatically gets a macro on the next sync without per-source configuration. Works for `DimensionTable`, `SnapshotTable`, and `M2MTable`.

### Data flow: raw -> canonical

1. **Sync**: Source fetches from API, dlt loads into source-specific schema (`garmin.*`, `lunchmoney.*`, `strava.*`, ...)
2. **Transform**: Configurable SQL transforms stored in DuckDB (`shenas_system.transforms`): DELETE by source, INSERT into `metrics.*` (runs automatically after sync)
3. **Visualize**: Frontend queries `metrics.*` via Arrow IPC

### Shared core packages

- **`shenas-source-core`** (`plugins/sources/core/`) — shared source utilities: `resolve_start_date`, `date_range`, `is_empty_response`, `create_pipe_app`, `run_sync`, `print_load_info`
- **`shenas-dataset-core`** (`plugins/datasets/core/`) — shared dataset utilities: `MetricTable` (the dataset-side `Table` subclass) and the `Dataset` plugin ABC

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
- **Plugin kinds**: source, dataset, dashboard, frontend, theme, analysis, transformation, model (all in `plugins/`)
- **Themes**: exclusive (only one enabled at a time), CSS custom properties pierce Shadow DOM
- **Python namespaces**: `shenas_sources.*`, `shenas_datasets.*`, `shenas_dashboards.*` (not `pipes.*` — conflicts with stdlib)
- **DuckDB schemas**: raw data in source-specific schemas (`garmin.*`, `lunchmoney.*`, `strava.*`, ...), canonical in `metrics.*`
- **Raw table semantics**: every raw source table inherits from one of `EventTable` | `IntervalTable` | `SnapshotTable` | `DimensionTable` | `AggregateTable` | `CounterTable` (in `shenas_sources.core.table`). The kind base class drives the dlt write_disposition automatically — see "Raw table semantics" above
- **Units: always SI** (or universally-accepted SI-derived / SI-prefixed) **unless there's an explicit reason not to**. Whenever you add a `Field()` annotation for a quantity column, set `unit="..."` and use one of: `m` (meters), `s` (seconds), `ms` (milliseconds), `kg` (kilograms), `W` (watts), `kJ` (kilojoules), `m/s`, `bpm`, `degC`, `kcal` (food convention), `percent`, `bytes`, `min`, `rpm`. Column names should match the unit suffix (`distance_m`, `moving_time_s`, `weight_kg`, ...). Imperial / non-SI is allowed only when the upstream API hands data over in those units AND converting would be lossy or surprising — when you do, document why in the field's description.

## Modules

- `app/` — FastAPI UI server (shenas-app); discovers plugins via entry points, serves Arrow IPC
- `app/graphql/` — Strawberry GraphQL schema, mutations, LLM provider routing
- `app/telemetry/` — OpenTelemetry exporters, DuckDB spans/logs, real-time SSE dispatcher
- `app/mesh/` — peer-to-peer mesh daemon, identity, relay sync, transport
- `app/fl/` — Flower FL client, PyTorch training, inference engine, model plugin registry
- `app/desktop/` — Tauri v2 desktop app with bundled PyInstaller sidecars
- `app/mobile/` — Tauri v2 mobile app (Rust core: axum + DuckDB, no Python)
- `app/vendor/` — shared frontend deps (Lit, Arrow, uPlot, Cytoscape) built with Rollup
- `shenasctl/` — lightweight CLI client (shenas-cli); httpx + typer + cryptography
- `scheduler/` — background sync daemon sidecar (shenas-scheduler); polls server for due pipes
- `server/api/` — shenas.net web API (LLM proxy, literature gateway, package repository)
- `server/fl/` — federated learning coordinator (Flower server + REST API); runs in its own venv
- `server/shenas.net/` — shenas.net marketing site (Astro)
- `server/shenas.org/` — shenas.org site (Astro)
- `server/deploy/` — Kubernetes, Terraform/OpenTofu, Docker deployment configs
- `scripts/` — build helpers (version bumping, pre-commit hook)
- `plugins/core/` — shared plugin utilities (shenas-plugin-core)
- `plugins/sources/core/` — shared source utilities (shenas-source-core)
- `plugins/sources/chrome/` — Chrome browser history
- `plugins/sources/cronometer/` — Cronometer nutrition tracking
- `plugins/sources/duolingo/` — Duolingo (XP, courses, profile, achievements, league, friends)
- `plugins/sources/firefox/` — Firefox browser history
- `plugins/sources/garmin/` — Garmin Connect (activities, daily stats, sleep, HRV, SpO2, body composition)
- `plugins/sources/gcalendar/` — Google Calendar (events with attendees + colors palette)
- `plugins/sources/github/` — GitHub activity
- `plugins/sources/gmail/` — Gmail (messages, labels, profile, filters, vacation, send_as)
- `plugins/sources/goodreads/` — Goodreads reading history
- `plugins/sources/gtakeout/` — Google Takeout import (photos, location, YouTube history)
- `plugins/sources/lunchmoney/` — Lunch Money (transactions, transaction_tags, categories, budgets, recurring, assets, plaid, user, crypto)
- `plugins/sources/obsidian/` — Obsidian daily notes (frontmatter extraction)
- `plugins/sources/rescuetime/` — RescueTime productivity tracking
- `plugins/sources/shell_history/` — shell command history
- `plugins/sources/spotify/` — Spotify (recently played, top tracks/artists for all 3 time ranges, saved tracks/albums/shows/episodes, playlists, followed artists, audio_features, user_profile)
- `plugins/sources/strava/` — Strava (activities with detail, laps, kudos, comments, athlete, athlete_stats, athlete_zones, gear)
- `plugins/sources/tile/` — Tile location tracking
- `plugins/sources/withings/` — Withings health devices
- `plugins/datasets/core/` — shared dataset utilities (shenas-dataset-core)
- `plugins/datasets/fitness/` — canonical fitness metrics (HRV, sleep, vitals, body)
- `plugins/datasets/finance/` — canonical finance metrics (transactions, spending, budgets)
- `plugins/datasets/events/` — unified event timeline
- `plugins/datasets/outcomes/` — canonical outcome metrics (mood, stress, productivity, exercise)
- `plugins/datasets/habits/` — canonical habits metrics (daily habits)
- `plugins/datasets/location/` — canonical location metrics
- `plugins/datasets/promoted/` — dynamically promoted hypothesis-to-metric tables
- `plugins/analyses/core/` — shared analysis utilities
- `plugins/analyses/hypothesis/` — hypothesis-driven analysis (Recipe DAG runner)
- `plugins/transformations/core/` — shared transformation utilities
- `plugins/transformations/*/` — transform plugins (sql, dedup-merge, geocode, geofence, reverse-geocode, regex-extract, llm-categorize)
- `plugins/models/core/` — shared ML model utilities
- `plugins/models/sleep-forecast/` — sleep quality forecasting model
- `plugins/dashboards/core/` — shared dashboard utilities
- `plugins/dashboards/fitness/` — Lit + uPlot fitness charts (built as wheel)
- `plugins/dashboards/data-table/` — Lit data table with sorting/filtering/pagination (built as wheel)
- `plugins/dashboards/event-gantt/` — event Gantt chart visualization
- `plugins/dashboards/timeline/` — timeline visualization
- `plugins/frontends/core/` — shared frontend utilities
- `plugins/frontends/default/` — default UI shell (Lit SPA with tabs, command palette, data flow graph)
- `plugins/frontends/focus/` — focus mode frontend
- `plugins/themes/core/` — shared theme utilities
- `plugins/themes/default/` — default light theme (CSS custom properties)
- `plugins/themes/dark/` — dark theme

## Git workflow

- Never commit directly to main. Always create a feature branch first.
- Use conventional branch names: `feat/`, `fix/`, `refactor/`, `chore/`
- When done with changes, push the branch and open a PR via `gh pr create`.

## Hooks

Ruff check, ruff format, and ty check run automatically after every .py file edit via PostToolUse hook — no need to run manually.

Pre-commit hook runs `ruff check`, `ruff format --check`, and `ty check` before every commit. Install with `make hooks-setup`.
