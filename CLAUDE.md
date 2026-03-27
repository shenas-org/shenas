# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Don't ask about doing 'cat', 'find', 'diff' or similar

## Commands

```bash
uv run python main.py          # run the pipeline
uv run ruff check .            # lint
uv run ruff format .           # format
uv run cz commit               # conventional commit
uv add <package>               # add a dependency
uv sync                        # install dependencies
```

## Stack

- **dlt** — data ingestion/pipeline framework
- **DuckDB** — local destination, database at `./data/local.duckdb` (also available via MCP server `duckdb`)
- **uv** — package manager (do not use pip directly)
- **rich** — terminal output formatting
- **typer** — CLI framework

## CLI

`shenas` is the project CLI (entry point in `cli/`). Run with `uv run shenas`.

## Modules

- `cli/` — `shenas` CLI; subcommands under `cli/commands/`
- `pipes/` — dlt connectors; `pipes/garmin/` fetches Garmin Connect data
- `pipe_repository_server/` — PEP 503 Simple Repository API server (FastAPI)

## Hooks

Ruff check and format run automatically after every file edit via PostToolUse hook — no need to run manually.
