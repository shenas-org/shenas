"""Shared analysis plugin utilities.

An analysis plugin registers an :class:`AnalysisMode` (the LLM-facing
strategy: prompt, operation subset, tool definition) and optionally new
:class:`Operation` subclasses that extend the recipe compiler's
vocabulary.

Subclass :class:`Analysis` and set ``mode_cls`` and (optionally)
``extra_operations``. Registration happens automatically on subclass
definition via ``__init_subclass__``.
"""

from __future__ import annotations

from typing import ClassVar

from shenas_plugins.core.analytics.mode import AnalysisMode, register_mode
from shenas_plugins.core.analytics.operations import Operation, register_operation
from shenas_plugins.core.plugin import Plugin


class Analysis(Plugin):
    """Base class for analysis plugins.

    Each analysis plugin provides one :class:`AnalysisMode` and zero or
    more new :class:`Operation` subclasses. Both are registered at class
    definition time so they're available as soon as the plugin is
    imported (which happens at entry-point discovery).

    Attributes
    ----------
    mode_cls
        The :class:`AnalysisMode` subclass this plugin provides.
    extra_operations
        New operations this plugin introduces. These are registered in
        the global operation registry so the recipe compiler can see
        them. Operations shared across modes (Lag, Rolling, etc.) are
        registered in ``operations.py`` and don't need to be listed here.
    """

    _kind = "analysis"
    display_name_plural: ClassVar[str | None] = "Analyses"
    _discovered: ClassVar[bool] = False

    mode_cls: ClassVar[type[AnalysisMode]]
    extra_operations: ClassVar[tuple[type[Operation], ...]] = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # Register new operations this plugin introduces.
        for op in cls.extra_operations:
            register_operation(op)
        # Register the mode.
        if hasattr(cls, "mode_cls") and cls.mode_cls is not AnalysisMode:
            register_mode(cls.mode_cls())

    @classmethod
    def discover(cls) -> None:
        """Load all analysis plugins via entry points.

        Importing an analysis plugin class triggers ``__init_subclass__``
        which auto-registers its mode and operations. Idempotent.
        """
        if cls._discovered:
            return
        cls._discovered = True
        import contextlib
        from importlib.metadata import entry_points

        for ep in entry_points(group=Plugin._ep_group("analysis")):
            with contextlib.suppress(Exception):
                ep.load()


Plugin._cache_clear_hooks.append(lambda: setattr(Analysis, "_discovered", False))

__all__ = ["Analysis", "AnalysisMode", "Operation", "register_mode", "register_operation"]
