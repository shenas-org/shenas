"""Base auth dataclass for all pipes.

Provides the common ``id`` field and the ``table_pk`` class var so
individual pipes only need to declare their credential fields and a
``table_name`` (set dynamically by ``Source.__init_subclass__``).
"""

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from app.table import Field, SingletonTable


@dataclass
class SourceAuth(SingletonTable):
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

    class _Meta(SingletonTable._Meta):
        display_name = "Source Auth"
        description = "Encrypted per-source credential storage."
        pk = ("id",)
        schema = "auth"

    id: Annotated[int, Field(db_type="INTEGER", description="Auth row identifier")] = 1

    def __init_subclass__(cls, **kwargs: Any) -> None:
        # Defer validation: mark abstract before Table.__init_subclass__
        # walks the dict, so its `if "_abstract" not in cls.__dict__: cls._abstract = False`
        # check leaves us alone.
        if "_abstract" not in cls.__dict__:
            cls._abstract = True
        super().__init_subclass__(**kwargs)
