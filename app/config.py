"""Shared configuration constants.

Centralizes env-var lookups so other modules import from here
instead of reading os.environ directly.
"""

from __future__ import annotations

import os

SHENAS_NET_URL = os.environ.get("SHENAS_NET_URL", "https://shenas.ai")

# Kanidm OAuth2 authorization-code + PKCE settings for the desktop/CLI app.
# KANIDM_URL must match the public GKE endpoint from Phase 1 v2 (SHE-355).
# The redirect URI must be pre-registered on the Kanidm client (see
# deploy/kanidm-k8s/scripts/register-shenas-ai-client.sh).
KANIDM_URL = os.environ.get("KANIDM_URL", "https://auth.shenas.net")
# Native-app sign-in uses a *public* OAuth2 client (no secret, PKCE only) per
# RFC 8252 §8.4. The confidential `shenas-ai` client is reserved for the web
# flow at server/api/. See deploy/kanidm-k8s/scripts/register-shenas-ai-desktop-client.sh.
KANIDM_CLIENT_ID = os.environ.get("KANIDM_CLIENT_ID", "shenas-ai-desktop")
KANIDM_CLIENT_SECRET = os.environ.get("KANIDM_CLIENT_SECRET", "")
KANIDM_SCOPE = os.environ.get("KANIDM_SCOPE", "openid email profile")
KANIDM_REDIRECT_URI = os.environ.get("KANIDM_REDIRECT_URI", "http://localhost:7280/callback")
