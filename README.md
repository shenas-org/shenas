<p align="center">
  <img src="app/static/images/shenas.png" width="96" alt="shenas">
</p>

<h1 align="center">shenas</h1>

<p align="center">
  <a href="https://github.com/afuncke/shenas/actions/workflows/ci.yml"><img src="https://github.com/afuncke/shenas/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/afuncke/244bc7a96fa33c93b77c16950e287366/raw/shenas-coverage.json" alt="Coverage">
</p>

Health and finance metrics aggregation platform. Collects data from multiple sources, normalizes it into canonical schemas, and visualizes it through pluggable web components.

## Quick start

```bash
uv sync
uv run shenasctl --help
```

## Development setup

```bash
make dev-install    # editable install all pipes, schemas, components
make setup-hooks    # install pre-commit hook (ruff + ty)
```

## Data pipeline

```bash
# Authenticate
uv run shenasctl pipe garmin auth
uv run shenasctl pipe lunchmoney auth
uv run shenasctl pipe gmail auth
uv run shenasctl pipe gcalendar auth
uv run shenasctl pipe gtakeout auth

# Configure obsidian vault path
uv run shenasctl config set pipe obsidian daily_notes_folder /path/to/vault/daily

# Sync raw data into DuckDB (also runs transform automatically)
uv run shenasctl pipe sync              # sync all installed pipes
uv run shenasctl pipe garmin sync       # sync a single pipe
uv run shenasctl pipe gtakeout sync     # sync Google Takeout (downloads from Drive)

# Check what's loaded
uv run shenasctl db status
```

## Package management

```bash
uv run shenasctl pipe list                # list installed pipes
uv run shenasctl pipe add garmin          # install from repository
uv run shenasctl pipe remove garmin       # uninstall
uv run shenasctl schema list              # list installed schemas
uv run shenasctl component list           # list installed components
```

## Visualization

```bash
# Build and install the dashboard component
moon run fitness-dashboard:build
uv pip install packages/shenas_component_fitness_dashboard-*.whl

# Start the UI
uv run shenas
# Open https://127.0.0.1:7280
```

## Package distribution

All pipes, schemas, and components are distributed as Ed25519-signed Python wheels via a PEP 503 repository server.

```bash
# Generate signing keys
uv run shenasrepoctl keygen

# Build and sign packages
moon run :build

# Vendor transitive dependencies
shenasrepoctl vendor garmin

# Start the repository server
make repository

# Install from the repository (in another terminal)
uv run shenasctl pipe add garmin
```

## Testing

```bash
moon run :test      # run all tests (271)
moon run :lint      # ruff check across all projects
make coverage       # tests with coverage report
```

## Architecture

```
app/                 FastAPI server + CLI (shenas-app)
  api/               REST API endpoints (Pydantic request/response models)
  cli/               CLI commands (pure REST client, no direct DB access)
  models/            shared Pydantic models for API types
  tests/             API endpoint tests
pipes/
  core/              shared pipe utilities (shenas-pipe-core)
  garmin/            Garmin Connect connector
  lunchmoney/        Lunch Money connector
  obsidian/          Obsidian daily notes (frontmatter extraction)
  gmail/             Gmail (OAuth2)
  gcalendar/         Google Calendar (OAuth2)
  gtakeout/          Google Takeout (Drive download + parse)
schemas/
  core/              shared schema utilities (shenas-schema-core)
  fitness/           HRV, sleep, vitals, body metrics
  finance/           transactions, spending, budgets
  outcomes/          mood, stress, productivity, exercise, etc.
components/
  fitness-dashboard/ Lit + uPlot dashboard (built as wheel)
  data-table/        sortable/filterable data table (built as wheel)
repository/          PEP 503 package server + Ed25519 signing
telemetry/           OpenTelemetry tracing/logging with DuckDB backend
```

**Data flow**: Source API -> dlt -> raw DuckDB tables -> SQL transform -> canonical `metrics.*` tables -> Arrow IPC -> web component

**Plugin system**: Pipes register via `shenas.pipes` entry points, schemas via `shenas.schemas`, components via `shenas.components`. The CLI and UI discover them at runtime.

**Core packages**: `shenas-pipe-core` and `shenas-schema-core` provide shared utilities (DRY). They are internal dependencies, not user-facing.
