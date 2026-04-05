"""Configuration from environment variables."""

from __future__ import annotations

import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://postgres@localhost:5432/shenas_net")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", os.urandom(32).hex())
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:4321")
