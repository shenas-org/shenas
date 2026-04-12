"""Smoke test: verify the app import chain resolves without errors.

This catches missing dependencies in app/pyproject.toml -- if a runtime
import fails, this test fails. Equivalent to running
``make app-install && shenas --no-tls`` and checking it doesn't crash
on startup.
"""

from __future__ import annotations


def test_app_imports() -> None:
    """Import app.main, which triggers the full import chain:
    main -> api -> sync -> sources -> dashboards/datasets/transforms/...
    main -> api -> graphql -> strawberry
    """
    from app import main  # noqa: F401


def test_cli_imports() -> None:
    """Import the CLI entry point."""
    from app import cli  # noqa: F401


def test_graphql_schema_imports() -> None:
    """Import the GraphQL layer (strawberry, mutations, queries, types)."""
    from app.graphql import graphql_app  # noqa: F401


def test_plugin_discovery_imports() -> None:
    """Import the plugin loader that touches all core packages."""
    from shenas_plugins.core.plugin import Plugin  # noqa: F401
