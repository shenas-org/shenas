"""PostgreSQL connection and schema setup."""

from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from shenas_net_api.config import DATABASE_URL

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    picture TEXT,
    google_id TEXT UNIQUE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    device_type TEXT NOT NULL,
    public_key TEXT NOT NULL,
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS device_endpoints (
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    endpoint_type TEXT NOT NULL,
    address TEXT NOT NULL,
    priority INT DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (device_id, endpoint_type, address)
);

CREATE TABLE IF NOT EXISTS sync_cursors (
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    peer_device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    last_sync_at TIMESTAMPTZ,
    last_event_id TEXT,
    PRIMARY KEY (device_id, peer_device_id)
);

CREATE TABLE IF NOT EXISTS workers (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    deployment_name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS llm_usage (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month TEXT NOT NULL,
    tokens_used BIGINT NOT NULL DEFAULT 0,
    monthly_limit BIGINT NOT NULL DEFAULT 1000000,
    PRIMARY KEY (user_id, month)
);
"""


def get_conn() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def ensure_schema() -> None:
    with get_conn() as conn:
        conn.execute(_SCHEMA)
        # Migration: add is_admin column if missing (existing DBs)
        conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT FALSE")
        # Promote the first registered user to admin
        conn.execute(
            "UPDATE users SET is_admin = TRUE"
            " WHERE id = (SELECT id FROM users ORDER BY created_at LIMIT 1)"
            " AND NOT EXISTS (SELECT 1 FROM users WHERE is_admin = TRUE)"
        )
