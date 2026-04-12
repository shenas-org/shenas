"""Integration test: real frontend plugins serve their HTML.

This test does NOT mock Frontend.load_all. It uses the real installed plugins
and verifies that GET / serves the actual default frontend HTML. The test
will FAIL (not skip) if the static/ directory hasn't been built, catching
the bug where build artifacts are missing after a fresh checkout or after
make dev forgets to build them.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from shenas_frontends.core import Frontend


class TestDefaultFrontendIntegration:
    """Verify the real default frontend is served end-to-end."""

    def test_default_frontend_is_discoverable(self) -> None:
        """The Frontend plugin class is loadable via entry points."""
        frontends = [cls for cls in Frontend.load_all() if cls.name == "default"]
        assert len(frontends) == 1, "default frontend should be installed"

    def test_default_frontend_static_html_exists(self) -> None:
        """The default frontend's static HTML file is on disk.

        This file is a build artifact (vite output). If missing, run:
            cd plugins/frontends/default && npm run build
        """
        cls = next(c for c in Frontend.load_all() if c.name == "default")
        html_file = cls.static_dir / cls.html
        assert html_file.exists(), f"{html_file} is missing -- run `npm run build` in plugins/frontends/default"

    def test_root_serves_default_frontend_html(self) -> None:
        """GET / returns the actual built default.html, not the fallback."""
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        # Positive assertion: the real default.html includes a script tag for the
        # built JS bundle. The fallback only mentions API endpoints.
        assert "default.js" in resp.text, (
            "GET / did not return the default frontend HTML -- "
            "check that plugins/frontends/default/shenas_frontends/default/static/default.html exists"
        )
