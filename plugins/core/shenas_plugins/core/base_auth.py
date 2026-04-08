"""Base auth dataclass for all pipes.

Provides the common ``id`` field and the ``table_pk`` class var so
individual pipes only need to declare their credential fields and a
``table_name`` (set dynamically by ``Source.__init_subclass__``).

Per-user isolation: ``read_row``, ``write_row``, and ``clear_rows`` are
overridden to route to ``auth_{user_id}`` schema when a user is active,
falling back to ``auth`` in single-user mode.  This happens transparently
via the ``user_schema()`` helper so callers never need to pass user_id.
"""

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from shenas_plugins.core.table import Field, Table


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
    """

    _abstract: ClassVar[bool] = True
    table_display_name: ClassVar[str] = "Source Auth"
    table_description: ClassVar[str | None] = "Encrypted per-source credential storage."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)
    table_schema: ClassVar[str | None] = "auth"

    id: Annotated[int, Field(db_type="INTEGER", description="Auth row identifier")] = 1

    def __init_subclass__(cls, **kwargs: Any) -> None:
        # Defer validation: mark abstract before Table.__init_subclass__
        # walks the dict, so its `if "_abstract" not in cls.__dict__: cls._abstract = False`
        # check leaves us alone.
        if "_abstract" not in cls.__dict__:
            cls._abstract = True
        super().__init_subclass__(**kwargs)

    @classmethod
    def _auth_schema(cls, schema: str | None) -> str:
        if schema is not None:
            return schema
        from app.user_context import user_schema

        return user_schema("auth")

    @classmethod
    def read_row(cls, *, schema: str | None = None) -> dict[str, Any] | None:
        return super().read_row(schema=cls._auth_schema(schema))

    @classmethod
    def write_row(cls, *, schema: str | None = None, **kwargs: Any) -> None:
        super().write_row(schema=cls._auth_schema(schema), **kwargs)

    @classmethod
    def clear_rows(cls, *, schema: str | None = None) -> None:
        super().clear_rows(schema=cls._auth_schema(schema))
