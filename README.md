<p align="center">
  <img src="app/static/images/shenas.png" width="96" alt="shenas">
</p>

<h1 align="center">shenas</h1>

<p align="center">
  <a href="https://github.com/afuncke/shenas/actions/workflows/ci.yml"><img src="https://github.com/afuncke/shenas/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/afuncke/244bc7a96fa33c93b77c16950e287366/raw/shenas-coverage.json" alt="Coverage">
</p>

A federated quantified-self platform where ML and AI coaches you without you ever giving up your data. Collects health, finance, and lifestyle metrics from multiple sources, normalizes them into canonical schemas, trains models locally via federated learning, and visualizes insights through pluggable web components.

## Quick start

```bash
uv sync
uv run shenasctl --help
```

## Development setup

```bash
make setup-hooks    # install pre-commit hook (ruff + ty)
make install        # install shenas + shenasrepoctl to ~/.local/bin/
```

## Data pipeline

```bash
# Authenticate
shenasctl pipe garmin auth
shenasctl pipe lunchmoney auth
shenasctl pipe gmail auth
shenasctl pipe gcalendar auth

# Configure obsidian vault path
shenasctl config set pipe obsidian vault_path /path/to/vault

# Sync raw data into DuckDB (also runs transform automatically)
shenasctl pipe sync          # sync all installed pipes
shenasctl pipe garmin sync   # sync a single pipe

# Check what's loaded
shenasctl db status
```

## Package management

```bash
shenasctl pipe list                # list installed pipes
shenasctl pipe add garmin          # install from repository
shenasctl pipe remove garmin       # uninstall
shenasctl schema list              # list installed schemas
shenasctl component list           # list installed components
```

## Visualization

```bash
# Install the dashboard component from the repository
shenasctl component add fitness-dashboard

# Start the UI
shenas
# Open https://127.0.0.1:7280
```

## Package distribution

All pipes, schemas, and components are distributed as Ed25519-signed Python wheels via a PEP 503 repository server.

```bash
# Generate signing keys
shenasrepoctl keygen

# Build and sign packages
moon run :build

# Vendor transitive dependencies
shenasrepoctl vendor garmin

# Start the repository server
make repository

# Install from the repository (in another terminal)
shenasctl pipe add garmin
```

## Testing

```bash
moon run :test      # run all tests
moon run :lint      # ruff check across all projects
make coverage       # tests with coverage report
make clean          # remove all build artifacts
```

## Architecture

```
app/                 FastAPI UI server (Arrow IPC queries)
app/telemetry/       OpenTelemetry exporters, DuckDB spans/logs, SSE dispatcher
app/vendor/          shared frontend deps (Lit, Arrow, uPlot, Cytoscape)
app/desktop/         Tauri desktop app with bundled PyInstaller sidecars
shenasctl/           lightweight CLI client (httpx + typer)
scheduler/           background sync daemon sidecar
server/repository/   PEP 503 package server + Ed25519 signing
plugins/
  core/              shared plugin utilities (shenas-plugin-core)
  pipes/core/        shared pipe utilities (shenas-pipe-core)
  pipes/garmin/      Garmin Connect connector
  pipes/gcalendar/   Google Calendar connector
  pipes/gtakeout/    Google Takeout import
  pipes/lunchmoney/  Lunch Money connector
  pipes/obsidian/    Obsidian daily notes (frontmatter)
  pipes/gmail/       Gmail (OAuth2)
  pipes/duolingo/    Duolingo (JWT browser auth)
  pipes/spotify/     Spotify (PKCE OAuth + history import)
  schemas/core/      shared schema utilities (shenas-schema-core)
  schemas/fitness/   HRV, sleep, vitals, body metrics
  schemas/finance/   transactions, spending, budgets
  schemas/events/    unified event timeline
  schemas/outcomes/  mood, stress, productivity, exercise
  schemas/habits/    daily habits
  components/        Lit web components (built as wheels)
  themes/            CSS custom properties (default + dark)
  uis/default/       default UI shell (Lit SPA with tabs, command palette)
```

**Data flow**: Source API -> dlt -> raw DuckDB tables -> SQL transform -> canonical `metrics.*` tables -> Arrow IPC -> web component

**Plugin system**: Pipes register via `shenas.pipes` entry points, schemas via `shenas.schemas`, components via `shenas.components`. The CLI and UI discover them at runtime via `importlib.metadata`.

**Core packages**: `shenas-pipe-core` and `shenas-schema-core` provide shared utilities. They are internal dependencies, not user-facing.
