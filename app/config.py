"""Shared configuration constants.

Centralizes env-var lookups so other modules import from here
instead of reading os.environ directly.
"""

from __future__ import annotations

import os

SHENAS_NET_URL = os.environ.get("SHENAS_NET_URL", "https://shenas.net")
SHENAS_NET_API_URL = os.environ.get("SHENAS_NET_API_URL", SHENAS_NET_URL + "/api")
