"""Backward-compat shim -- re-exports TransformInstance as Transform.

All transform logic now lives in ``shenas_transformations.core.instance``.
"""

from shenas_transformations.core.instance import TransformInstance as Transform

__all__ = ["Transform"]
