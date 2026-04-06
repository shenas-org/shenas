"""Tests for app.api.pipes -- plugin loader functions."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest

from app.api.pipes import (
    _clear_caches,
    _group,
    _load_pipe,
    _load_plugin,
    _load_plugin_fresh,
    _load_plugins,
    _pipe_cache,
)
from shenas_plugins.core import Plugin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakePlugin(Plugin):
    name = "fake"
    display_name = "Fake Plugin"
    internal: ClassVar[bool] = False

    def resources(self, client):
        return []


class _InternalPlugin(Plugin):
    name = "internal"
    display_name = "Internal Plugin"
    internal: ClassVar[bool] = True

    def resources(self, client):
        return []


def _make_entry_point(name: str, obj: object, *, raises: bool = False) -> MagicMock:
    ep = MagicMock()
    ep.name = name
    if raises:
        ep.load.side_effect = ImportError("boom")
    else:
        ep.load.return_value = obj
    return ep


# ---------------------------------------------------------------------------
# _group
# ---------------------------------------------------------------------------


class TestGroup:
    def test_pipe(self) -> None:
        assert _group("pipe") == "shenas.pipes"

    def test_theme(self) -> None:
        assert _group("theme") == "shenas.themes"

    def test_component(self) -> None:
        assert _group("component") == "shenas.components"

    def test_schema(self) -> None:
        assert _group("schema") == "shenas.schemas"

    def test_ui_special_case(self) -> None:
        assert _group("ui") == "shenas.ui"


# ---------------------------------------------------------------------------
# _load_plugins
# ---------------------------------------------------------------------------


class TestLoadPlugins:
    def test_loads_all(self) -> None:
        eps = [_make_entry_point("a", _FakePlugin), _make_entry_point("b", _FakePlugin)]
        with patch("app.api.pipes.entry_points", return_value=eps):
            result = _load_plugins("pipe", base=Plugin)
        assert result == [_FakePlugin, _FakePlugin]

    def test_excludes_internal_when_requested(self) -> None:
        eps = [
            _make_entry_point("a", _FakePlugin),
            _make_entry_point("b", _InternalPlugin),
        ]
        with patch("app.api.pipes.entry_points", return_value=eps):
            result = _load_plugins("pipe", base=Plugin, include_internal=False)
        assert result == [_FakePlugin]

    def test_includes_internal_by_default(self) -> None:
        eps = [
            _make_entry_point("a", _FakePlugin),
            _make_entry_point("b", _InternalPlugin),
        ]
        with patch("app.api.pipes.entry_points", return_value=eps):
            result = _load_plugins("pipe", base=Plugin)
        assert len(result) == 2

    def test_skips_non_subclass(self) -> None:
        """Non-Plugin objects are silently skipped."""
        eps = [_make_entry_point("bad", str)]
        with patch("app.api.pipes.entry_points", return_value=eps):
            result = _load_plugins("pipe", base=Plugin)
        assert result == []

    def test_skips_on_import_error(self) -> None:
        eps = [_make_entry_point("broken", None, raises=True)]
        with patch("app.api.pipes.entry_points", return_value=eps):
            result = _load_plugins("pipe", base=Plugin)
        assert result == []

    def test_skips_non_class_objects(self) -> None:
        """Instances (not types) are skipped because isinstance(obj, type) is False."""
        eps = [_make_entry_point("instance", _FakePlugin())]
        with patch("app.api.pipes.entry_points", return_value=eps):
            result = _load_plugins("pipe", base=Plugin)
        assert result == []


# ---------------------------------------------------------------------------
# _load_plugin
# ---------------------------------------------------------------------------


class TestLoadPlugin:
    def test_finds_by_name(self) -> None:
        eps = [
            _make_entry_point("alpha", _FakePlugin),
            _make_entry_point("beta", _InternalPlugin),
        ]
        with patch("app.api.pipes.entry_points", return_value=eps):
            result = _load_plugin("pipe", "alpha")
        assert result is _FakePlugin

    def test_returns_none_for_missing(self) -> None:
        eps = [_make_entry_point("alpha", _FakePlugin)]
        with patch("app.api.pipes.entry_points", return_value=eps):
            result = _load_plugin("pipe", "nope")
        assert result is None

    def test_returns_none_on_import_error(self) -> None:
        eps = [_make_entry_point("broken", None, raises=True)]
        with patch("app.api.pipes.entry_points", return_value=eps):
            result = _load_plugin("pipe", "broken")
        assert result is None

    def test_returns_none_for_non_plugin(self) -> None:
        """Entry point loads a non-Plugin class -> returns None and breaks."""
        eps = [_make_entry_point("bad", str)]
        with patch("app.api.pipes.entry_points", return_value=eps):
            result = _load_plugin("pipe", "bad")
        assert result is None


# ---------------------------------------------------------------------------
# _load_pipe
# ---------------------------------------------------------------------------


class _FakePipe:
    """Minimal fake that avoids inheriting from the real Pipe (which needs DB)."""

    name = "testpipe"


class TestLoadPipe:
    def setup_method(self) -> None:
        _pipe_cache.clear()

    def teardown_method(self) -> None:
        _pipe_cache.clear()

    def test_returns_cached(self) -> None:
        sentinel = _FakePipe()
        _pipe_cache["testpipe"] = sentinel
        result = _load_pipe("testpipe")
        assert result is sentinel

    def test_loads_from_entry_points(self) -> None:
        ep = MagicMock()
        ep.name = "mypipe"
        instance = _FakePipe()
        ep.load.return_value = lambda: instance  # cls() returns instance
        # Make cls() work: ep.load returns a callable that returns instance
        ep.load.return_value = MagicMock(return_value=instance)
        with patch("app.api.pipes.entry_points", return_value=[ep]):
            result = _load_pipe("mypipe")
        assert result is instance
        assert _pipe_cache["mypipe"] is instance

    def test_falls_back_to_fresh_scan(self) -> None:
        """When entry_points misses the pipe, _load_plugin_fresh is tried."""
        instance = _FakePipe()
        cls_mock = MagicMock(return_value=instance)
        with (
            patch("app.api.pipes.entry_points", return_value=[]),
            patch("app.api.pipes._load_plugin_fresh", return_value=cls_mock),
        ):
            result = _load_pipe("testpipe")
        assert result is instance
        assert _pipe_cache["testpipe"] is instance

    def test_raises_when_not_found(self) -> None:
        with (
            patch("app.api.pipes.entry_points", return_value=[]),
            patch("app.api.pipes._load_plugin_fresh", return_value=None),
            pytest.raises(ValueError, match="Pipe not found: nope"),
        ):
            _load_pipe("nope")


# ---------------------------------------------------------------------------
# _clear_caches
# ---------------------------------------------------------------------------


class TestClearCaches:
    def setup_method(self) -> None:
        _pipe_cache.clear()

    def test_clears_pipe_cache(self) -> None:
        _pipe_cache["x"] = "dummy"
        _clear_caches()
        assert _pipe_cache == {}

    def test_calls_invalidate_caches(self) -> None:
        with patch("importlib.invalidate_caches") as mock_inv:
            _clear_caches()
        mock_inv.assert_called_once()

    def test_clears_fast_path_cache(self) -> None:
        """If FastPath.__new__ has cache_clear, it should be called."""
        cache_clear = MagicMock()

        class FakeFastPath:
            pass

        FakeFastPath.__new__ = MagicMock()  # type: ignore[assignment]
        FakeFastPath.__new__.cache_clear = cache_clear  # type: ignore[attr-defined]
        with (
            patch("importlib.metadata.FastPath", FakeFastPath, create=True),
            patch("importlib.invalidate_caches"),
        ):
            _clear_caches()
        cache_clear.assert_called_once()

    def test_removes_site_packages_from_importer_cache(self) -> None:
        fake_key = "/fake/site-packages"
        sys.path_importer_cache[fake_key] = MagicMock()
        try:
            _clear_caches()
            assert fake_key not in sys.path_importer_cache
        finally:
            sys.path_importer_cache.pop(fake_key, None)


# ---------------------------------------------------------------------------
# _load_plugin_fresh
# ---------------------------------------------------------------------------


class TestLoadPluginFresh:
    def test_finds_plugin_on_disk(self, tmp_path) -> None:
        """Simulate a dist-info dir with an entry point matching our target."""
        # The path must contain "site-packages" for _load_plugin_fresh to scan it
        site_dir = tmp_path / "lib" / "site-packages"
        site_dir.mkdir(parents=True)

        mod_name = "_test_fake_pipe_mod"
        mod = MagicMock()
        mod.MyPipe = _FakePlugin  # a real Plugin subclass

        fake_ep = SimpleNamespace(
            group="shenas.pipes",
            name="fakepipe",
            value=f"{mod_name}:MyPipe",
        )
        fake_dist = MagicMock()
        fake_dist.entry_points = [fake_ep]

        # Create a .dist-info directory inside site-packages
        (site_dir / "fakepkg.dist-info").mkdir()

        with (
            patch.object(sys, "path", [str(site_dir)]),
            patch("importlib.metadata.PathDistribution", return_value=fake_dist),
            patch.dict(sys.modules, {mod_name: mod}),
            patch("importlib.import_module", return_value=mod),
        ):
            result = _load_plugin_fresh("pipe", "fakepipe")

        assert result is _FakePlugin

    def test_returns_none_when_not_found(self, tmp_path) -> None:
        site_dir = str(tmp_path / "site-packages")
        (tmp_path / "site-packages").mkdir()
        with patch.object(sys, "path", [site_dir]):
            result = _load_plugin_fresh("pipe", "nonexistent")
        assert result is None

    def test_skips_non_site_packages(self) -> None:
        """Paths without 'site-packages' are ignored."""
        with patch.object(sys, "path", ["/usr/lib/python3"]):
            result = _load_plugin_fresh("pipe", "any")
        assert result is None

    def test_handles_import_error(self, tmp_path) -> None:
        """If the module import fails, returns None."""
        fake_ep = SimpleNamespace(
            group="shenas.pipes",
            name="broken",
            value="no_such_mod:Cls",
        )
        fake_dist = MagicMock()
        fake_dist.entry_points = [fake_ep]

        fake_dist_info = tmp_path / "brokenpkg.dist-info"
        fake_dist_info.mkdir()

        site_dir = str(tmp_path)

        with (
            patch.object(sys, "path", [site_dir]),
            patch("importlib.metadata.PathDistribution", return_value=fake_dist),
            patch("importlib.import_module", side_effect=ImportError("no module")),
        ):
            result = _load_plugin_fresh("pipe", "broken")

        assert result is None
