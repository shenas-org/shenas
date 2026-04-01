"""Skip all FL tests when torch is not installed."""

import pytest

try:
    import torch  # noqa: F401
except ImportError:
    pytest.skip("FL dependencies not installed (uv sync --group fl)", allow_module_level=True)
