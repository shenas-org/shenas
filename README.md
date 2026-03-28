# shenas

[![CI](https://github.com/afuncke/shenas/actions/workflows/ci.yml/badge.svg)](https://github.com/afuncke/shenas/actions/workflows/ci.yml)
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/afuncke/244bc7a96fa33c93b77c16950e287366/raw/shenas-coverage.json)

Health and finance metrics aggregation platform. Collects data from multiple sources, normalizes it into canonical schemas, and visualizes it through pluggable web components.

## Quick start

```bash
uv sync
uv run shenas --help
```

## Development setup

```bash
make dev-install    # editable install all pipes, schemas, components
make setup-hooks    # install pre-commit hook (ruff + ty)
```

## Data pipeline

```bash
# Authenticate
uv run shenas pipe garmin auth
uv run shenas pipe lunchmoney auth

# Sync raw data into DuckDB (also runs transform automatically)
uv run shenas pipe garmin sync
uv run shenas pipe lunchmoney sync

# Check what's loaded
uv run shenas data status
```

## Package management

```bash
uv run shenas pipe list                # list installed pipes
uv run shenas pipe add garmin          # install from repository
uv run shenas pipe remove garmin       # uninstall
uv run shenas schema list              # list installed schemas
uv run shenas component list           # list installed components
```

## Visualization

```bash
# Build and install the dashboard component
make build-components COMPONENT=fitness-dashboard
uv pip install packages/shenas_component_fitness_dashboard-*.whl

# Start the UI
uv run shenas ui
# Open http://127.0.0.1:7280
```

## Package distribution

All pipes, schemas, and components are distributed as Ed25519-signed Python wheels via a PEP 503 repository server.

```bash
# Generate signing keys
uv run shenas registry keygen

# Build and sign packages
make build-schemas
make build-pipes
make build-components

# Vendor transitive dependencies
make vendor PIPE=garmin

# Start the repository server
make repository

# Install from the repository (in another terminal)
uv run shenas pipe add garmin
```

## Testing

```bash
make test           # run all tests (161)
make coverage       # tests with coverage report
make lint           # ruff check + format + ty
```

## Architecture

```
pipes/
  core/              shared pipe utilities (shenas-pipe-core)
  garmin/            Garmin Connect connector
  lunchmoney/        Lunch Money connector
schemas/
  core/              shared schema utilities (shenas-schema-core)
  fitness/   HRV, sleep, vitals, body metrics
  finance/           transactions, spending, budgets
components/
  fitness-dashboard/ Lit + uPlot dashboard (built as wheel)
local_frontend/      FastAPI UI server (Arrow IPC queries)
repository/          PEP 503 package server + Ed25519 signing
cli/                 shenas CLI
tests/               repository server, frontend, CLI, signing tests
```

**Data flow**: Source API -> dlt -> raw DuckDB tables -> SQL transform -> canonical `metrics.*` tables -> Arrow IPC -> web component

**Plugin system**: Pipes register via `shenas.pipes` entry points, schemas via `shenas.schemas`, components via `shenas.components`. The CLI and UI discover them at runtime.

**Core packages**: `shenas-pipe-core` and `shenas-schema-core` provide shared utilities (DRY). They are internal dependencies, not user-facing.
