from shenas_plugins.core.base_auth import SourceAuth
from shenas_plugins.core.base_config import SourceConfig
from shenas_plugins.core.plugin import Plugin, _SelectOneMixin
from shenas_plugins.core.static import StaticPlugin
from shenas_plugins.core.store import DataclassStore

__all__ = [
    "Dashboard",
    "DataclassStore",
    "Dataset",
    "Frontend",
    "Plugin",
    "Source",
    "SourceAuth",
    "SourceConfig",
    "StaticPlugin",
    "Theme",
    "_SelectOneMixin",
]

# Lazy re-exports from per-kind core packages to avoid circular imports.
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "Source": ("shenas_sources.core.source", "Source"),
    "Dataset": ("shenas_datasets.core.dataset", "Dataset"),
    "Theme": ("shenas_themes.core", "Theme"),
    "Frontend": ("shenas_frontends.core", "Frontend"),
    "Dashboard": ("shenas_dashboards.core", "Dashboard"),
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        import importlib

        mod = importlib.import_module(module_path)
        value = getattr(mod, attr)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
