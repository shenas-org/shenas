# shenas

Health metrics aggregation platform. Collects data from multiple sources, normalizes it into a canonical schema, and visualizes it through pluggable web components.

## Quick start

```bash
uv sync
uv run shenas --help
```

## Development setup

Install pipes and schemas for local development:

```bash
uv pip install -e schemas/fitness_tracker
uv pip install -e pipes/garmin
```

## Data pipeline

```bash
# Authenticate with Garmin Connect
uv run shenas pipe garmin auth

# Sync raw data into DuckDB
uv run shenas pipe garmin sync

# Transform raw data into canonical metrics
uv run shenas pipe garmin transform

# Check what's loaded
uv run shenas data status
```

## Visualization

```bash
# Build and install the dashboard component
make build-components COMPONENT=fitness-dashboard
uv pip install packages/shenas_component_fitness_dashboard-*.whl

# Start the UI
uv run shenas ui
# Open http://127.0.0.1:8000
```

## Package distribution

All pipes, schemas, and components are distributed as signed Python wheels via a PEP 503 repository server.

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
make repository_server

# Install from the repository (in another terminal)
uv run shenas install pipe garmin
```

## Architecture

```
pipes/                   dlt connectors (standalone packages)
schemas/                 canonical metric schemas (standalone packages)
local_frontend/          FastAPI UI server (Arrow IPC queries)
frontend_components/     web components (Lit + uPlot, built as wheels)
repository_server/       PEP 503 package server
registry/                Ed25519 signing
cli/                     shenas CLI
```

**Data flow**: Source API -> dlt -> raw DuckDB tables -> SQL transform -> canonical `metrics.*` tables -> Arrow IPC -> web component

**Plugin system**: Pipes register via `shenas.pipes` entry points, schemas via `shenas.schemas`, components via `shenas.components`. The CLI and UI discover them at runtime.
