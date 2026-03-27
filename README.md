# shenas

Health metrics aggregation platform. Collects data from multiple sources, normalizes it into a canonical schema, and visualizes it through pluggable web components.

## Quick start

```bash
uv sync
uv run shenas --help
```

## Data pipeline

```bash
# Authenticate with Garmin Connect
uv run shenas --dev pipe garmin auth

# Sync raw data into DuckDB
uv run shenas --dev pipe garmin sync

# Transform raw data into canonical metrics
uv run shenas --dev pipe garmin transform

# Check what's loaded
uv run shenas data status
```

## Visualization

```bash
# Build and install the dashboard component
make build-components COMPONENT=dashboard
uv pip install packages/shenas_component_dashboard-*.whl

# Start the UI
uv run shenas ui
# Open http://127.0.0.1:8000
```

## Package distribution

All pipes and components are distributed as signed Python wheels via a PEP 503 repository server.

```bash
# Generate signing keys
uv run shenas registry keygen

# Build and sign packages
make build-pipes
make build-components

# Vendor transitive dependencies
make vendor PIPE=garmin

# Start the repository server
make repository_server

# Install from the repository (in another terminal)
uv run shenas install pipe garmin
```

## Development

Use `--dev` to load pipes from local source without installing:

```bash
uv run shenas --dev pipe garmin sync
uv run shenas --dev pipe list          # shows "dev" instead of signature status
```

## Architecture

```
pipes/                   dlt connectors (standalone packages)
schema/                  canonical metric types + DDL generation
local_frontend/          FastAPI UI server (Arrow IPC queries)
frontend_components/     web components (Lit + uPlot, built as wheels)
repository_server/  PEP 503 package server
registry/                Ed25519 signing
cli/                     shenas CLI
```

**Data flow**: Source API -> dlt -> raw DuckDB tables -> SQL transform -> canonical `metrics.*` tables -> Arrow IPC -> web component

**Plugin system**: Pipes register via `shenas.pipes` entry points, components via `shenas.components`. The CLI and UI discover them at runtime.
