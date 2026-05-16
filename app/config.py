"""Shared configuration constants.

Centralizes env-var lookups so other modules import from here
instead of reading os.environ directly.
"""

from __future__ import annotations

import os

SHENAS_NET_URL = os.environ.get("SHENAS_NET_URL", "https://shenas.ai")

# Kanidm device-authorization-grant settings for the desktop/CLI app.
# KANIDM_URL must match the public GKE endpoint from Phase 1 v2 (SHE-355).
KANIDM_URL = os.environ.get("KANIDM_URL", "")
KANIDM_CLIENT_ID = os.environ.get("KANIDM_CLIENT_ID", "shenas-ai")
KANIDM_DEVICE_SCOPE = os.environ.get("KANIDM_DEVICE_SCOPE", "openid email profile")
