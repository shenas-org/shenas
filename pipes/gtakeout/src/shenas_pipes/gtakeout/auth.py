"""Google Drive OAuth2 -- delegates to shared GoogleAuth."""

from __future__ import annotations

from shenas_pipes.core.google_auth import GoogleAuth

_auth = GoogleAuth("gtakeout", ["https://www.googleapis.com/auth/drive.readonly"], "drive", "v3")

AUTH_FIELDS = _auth.AUTH_FIELDS
build_client = _auth.build_client
authenticate = _auth.authenticate
