# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
- **DuckDB** — local destination for loaded data
- **uv** — package manager (do not use pip directly)
