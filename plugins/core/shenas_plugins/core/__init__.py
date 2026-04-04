from shenas_plugins.core.base_auth import PipeAuth
from shenas_plugins.core.base_config import PipeConfig
from shenas_plugins.core.plugin import Plugin, _SelectOneMixin
from shenas_plugins.core.static import StaticPlugin
from shenas_plugins.core.store import DataclassStore

__all__ = [
    "UI",
    "Component",
    "DataclassStore",
    "Pipe",
    "PipeAuth",
    "PipeConfig",
    "Plugin",
    "Schema",
    "StaticPlugin",
    "Theme",
    "_SelectOneMixin",
]

# Lazy re-exports from per-kind core packages to avoid circular imports.
# These packages depend on shenas_plugins.core.plugin / .static, so importing
# them eagerly at module level would create a cycle.
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "Pipe": ("shenas_pipes.core.pipe", "Pipe"),
    "Schema": ("shenas_schemas.core.schema", "Schema"),
    "Theme": ("shenas_themes.core", "Theme"),
    "UI": ("shenas_ui.core", "UI"),
    "Component": ("shenas_components.core", "Component"),
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
