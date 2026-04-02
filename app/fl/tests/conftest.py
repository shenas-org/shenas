"""Skip all FL tests when torch is not installed."""

_torch_available = False
try:
    import torch  # noqa: F401

    _torch_available = True
except ImportError:
    pass

collect_ignore_glob = [] if _torch_available else ["test_*.py"]
