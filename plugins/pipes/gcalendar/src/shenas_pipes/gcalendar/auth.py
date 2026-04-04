"""Google Calendar OAuth2 -- delegates to shared GoogleAuth."""

from __future__ import annotations

from shenas_pipes.core.google_auth import GoogleAuth

_auth = GoogleAuth("gcalendar", ["https://www.googleapis.com/auth/calendar.readonly"], "calendar", "v3")

AUTH_FIELDS = _auth.AUTH_FIELDS
AUTH_INSTRUCTIONS = _auth.AUTH_INSTRUCTIONS
build_client = _auth.build_client
authenticate = _auth.authenticate
