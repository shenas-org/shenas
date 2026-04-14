"""Configuration from environment variables."""

from __future__ import annotations

import logging
import os
from pathlib import Path

# Load .env from the api directory if it exists
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    for raw in _env_file.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://postgres@localhost:5432/shenas_net")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
SESSION_SECRET = os.environ.get("SESSION_SECRET", os.urandom(32).hex())
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:4321")

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    logging.getLogger("shenas-net-api").warning(
        "GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set. "
        "Google sign-in will not work. "
        "Add them to server/api/.env or pass as environment variables."
    )
