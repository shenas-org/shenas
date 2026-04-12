"""Backward-compat shim -- re-exports Transform as Transform.

All transform logic now lives in ``shenas_transformers.core.transform``.
"""

from shenas_transformers.core.transform import Transform as Transform

__all__ = ["Transform"]
