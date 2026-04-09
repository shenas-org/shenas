"""Built-in analysis modes.

Importing this package auto-registers every built-in mode. External
code that needs modes should ``import shenas_plugins.core.analytics.modes``
(or rely on the analytics ``__init__`` which does it) before calling
:func:`get_mode`.
"""

from shenas_plugins.core.analytics.modes.hypothesis import HypothesisMode

__all__ = ["HypothesisMode"]
