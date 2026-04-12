"""Backward-compat shim -- re-exports TransformInstance as Transform.

All transform logic now lives in ``shenas_transformers.core.instance``.
"""

from shenas_transformers.core.instance import TransformInstance as Transform

__all__ = ["Transform"]
