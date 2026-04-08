"""Base auth dataclass for all pipes.

Provides the common ``id`` field and the ``table_pk`` class var so
individual pipes only need to declare their credential fields and a
``table_name`` (set dynamically by ``Source.__init_subclass__``).

In single-user mode ``id`` is always 1 (the original behaviour).  In
multi-user mode ``id`` equals the active ``user_id`` so each user has
their own credential row in the same table.

``read_row`` and ``write_row`` are overridden to be user-ID-aware, so
all individual source ``authenticate()`` methods that call
``self.Auth.read_row()`` / ``self.Auth.write_row()`` automatically get
per-user credential scoping without any changes.
"""

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from shenas_plugins.core.table import Field, Table


def _active_auth_id() -> int:
    """Return the id to use for auth storage.

    In single-user mode (no active LocalSession) returns 1 (backward-compatible).
    In multi-user mode returns the active user_id.
    """
    try:
        from app.local_sessions import LocalSession

        row = LocalSession.read_row()
        uid = row.get("user_id") if row else None
        return uid if uid is not None else 1
    except Exception:
        return 1


@dataclass
class SourceAuth(Table):
    """Base authentication storage for all pipes.

    ``table_name`` is set lazily by ``Source.__init_subclass__`` (one
    per pipe, like ``pipe_garmin``), so per-source ``Auth`` subclasses
    can't be validated at class-definition time. We override
    ``__init_subclass__`` to keep every direct subclass marked abstract
    so the parent ``Table`` machinery skips its auto-@dataclass +
    validate. ``Source.__init_subclass__`` calls
    :func:`finalize_pipe_table` after setting ``table_name`` to actually
    apply the dataclass + validation.

    The ``id`` field doubles as the user key:

    - Single-user mode: ``id = 1`` (original behaviour, no migration needed).
    - Multi-user mode: ``id = active_user_id`` so each user stores their own
      credentials independently in the same table.
    """

    _abstract: ClassVar[bool] = True
    table_display_name: ClassVar[str] = "Source Auth"
    table_description: ClassVar[str | None] = "Encrypted per-source credential storage."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)
    table_schema: ClassVar[str | None] = "auth"

    id: Annotated[int, Field(db_type="INTEGER", description="Auth row identifier (equals user_id in multi-user mode)")] = 1

    def __init_subclass__(cls, **kwargs: Any) -> None:
        # Defer validation: mark abstract before Table.__init_subclass__
        # walks the dict, so its `if "_abstract" not in cls.__dict__: cls._abstract = False`
        # check leaves us alone.
        if "_abstract" not in cls.__dict__:
            cls._abstract = True
        super().__init_subclass__(**kwargs)

    @classmethod
    def read_row(cls, *, schema: str | None = None) -> dict[str, Any] | None:
        """Read credentials for the active user.

        Overrides ``Table.read_row`` to use ``WHERE id = <user_id>`` instead
        of ``LIMIT 1`` so multi-user deployments isolate credentials per user.
        Single-user mode is unchanged (id = 1).
        """
        import dataclasses

        from app.db import cursor

        s = cls._resolve_schema(schema)
        cls._ensure_once(s)
        uid = _active_auth_id()
        cols = [f.name for f in dataclasses.fields(cls)]
        col_list = ", ".join(cols)
        with cursor() as cur:
            row = cur.execute(
                f"SELECT {col_list} FROM {s}.{cls.table_name} WHERE id = ?", [uid]
            ).fetchone()
        if row is None:
            return None
        return dict(zip(cols, row, strict=False))

    @classmethod
    def write_row(cls, *, schema: str | None = None, **kwargs: Any) -> None:
        """Write credentials for the active user.

        Overrides ``Table.write_row`` to upsert only the active user's row
        (using ``ON CONFLICT (id) DO UPDATE``), leaving other users'
        credentials untouched.
        """
        import dataclasses

        from app.db import cursor

        s = cls._resolve_schema(schema)
        cls._ensure_once(s)

        uid = _active_auth_id()
        existing = cls.read_row(schema=s)
        if existing:
            merged = {**existing, **kwargs}
        else:
            defaults: dict[str, Any] = {}
            for f in dataclasses.fields(cls):
                if f.default is not dataclasses.MISSING:
                    defaults[f.name] = f.default
                elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
                    defaults[f.name] = f.default_factory()  # type: ignore[misc]
                else:
                    defaults[f.name] = None
            merged = {**defaults, **kwargs}

        merged["id"] = uid
        cols = [f.name for f in dataclasses.fields(cls)]
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        set_clause = ", ".join(f"{c} = excluded.{c}" for c in cols if c != "id")
        values = [merged.get(c) for c in cols]
        with cursor() as cur:
            cur.execute(
                f"INSERT INTO {s}.{cls.table_name} ({col_names}) VALUES ({placeholders})"
                f" ON CONFLICT (id) DO UPDATE SET {set_clause}",
                values,
            )

    @classmethod
    def clear_rows(cls, *, schema: str | None = None) -> None:
        """Delete credentials for the active user only.

        Overrides ``Table.clear_rows`` -- in single-user mode this has the
        same effect as deleting all rows (there is only one); in multi-user
        mode only the active user's credentials are removed.
        """
        from app.db import cursor

        s = cls._resolve_schema(schema)
        cls._ensure_once(s)
        uid = _active_auth_id()
        with cursor() as cur:
            cur.execute(f"DELETE FROM {s}.{cls.table_name} WHERE id = ?", [uid])
