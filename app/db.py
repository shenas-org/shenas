"""Centralized DuckDB connection pool with encryption at rest.

Provides two long-lived connections:
- A read-only connection for queries (shared across API requests)
- A read-write connection for mutations (serialized via lock)

Both are created lazily on first use and reused across the server lifetime.
"""

import os
import secrets
import threading
from pathlib import Path

import duckdb

DB_PATH = Path("data") / "shenas.duckdb"

_reader: duckdb.DuckDBPyConnection | None = None
_writer: duckdb.DuckDBPyConnection | None = None
_reader_lock = threading.Lock()
_writer_lock = threading.Lock()


def get_db_key() -> str:
    """Get the database encryption key from env var or OS keyring."""
    key = os.environ.get("SHENAS_DB_KEY")
    if key:
        return key
    import keyring

    key = keyring.get_password("shenas", "db_key")
    if key:
        return key
    raise RuntimeError("No database key found. Run 'shenasctl db keygen' or set SHENAS_DB_KEY.")


def set_db_key(key: str) -> None:
    """Store the database encryption key in the OS keyring."""
    import keyring

    try:
        keyring.delete_password("shenas", "db_key")
    except Exception:
        pass
    keyring.set_password("shenas", "db_key", key)


def generate_db_key() -> str:
    """Generate a random 256-bit key as a hex string."""
    return secrets.token_hex(32)


def _create_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Create a new DuckDB connection attached to the encrypted file."""
    key = get_db_key()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    ro = ", READ_ONLY true" if read_only else ""
    con.execute(f"ATTACH '{DB_PATH}' AS db (ENCRYPTION_KEY '{key}'{ro})")
    con.execute("USE db")
    return con


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Get a pooled DuckDB connection.

    Read-only requests share a single long-lived reader connection.
    Write requests share a single writer connection, serialized via lock.

    Callers should NOT close the returned connection -- it's pooled.
    For read-only, call connect(read_only=True).
    """
    if read_only:
        return _get_reader()
    return _get_writer()


def _get_reader() -> duckdb.DuckDBPyConnection:
    global _reader
    if _reader is not None:
        return _reader
    with _reader_lock:
        if _reader is None:
            _reader = _create_connection(read_only=True)
        return _reader


def _get_writer() -> duckdb.DuckDBPyConnection:
    global _writer
    if _writer is not None:
        return _writer
    with _writer_lock:
        if _writer is None:
            _writer = _create_connection(read_only=False)
        return _writer


def acquire_writer() -> duckdb.DuckDBPyConnection:
    """Acquire exclusive access to the write connection.

    Returns the writer connection with the lock held.
    Caller MUST call release_writer() when done.
    """
    _writer_lock.acquire()
    return _get_writer()


def release_writer() -> None:
    """Release the write connection lock."""
    _writer_lock.release()


def close_writer() -> None:
    """Close the write connection and release the file lock.

    Used before operations that need exclusive file access
    (e.g. flush_to_encrypted which ATTACHes from a different connection).
    """
    global _writer
    with _writer_lock:
        if _writer is not None:
            _writer.close()
            _writer = None


def close_all() -> None:
    """Close all pooled connections. Called on shutdown."""
    global _reader, _writer
    with _reader_lock:
        if _reader is not None:
            _reader.close()
            _reader = None
    with _writer_lock:
        if _writer is not None:
            _writer.close()
            _writer = None
