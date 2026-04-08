"""Base config dataclass for all pipes.

Provides the common fields (``id``, ``sync_frequency``, ``lookback_period``)
and the ``table_pk`` class var so individual pipes only need to declare
their custom fields and a ``table_name`` (set dynamically by
``Source.__init_subclass__``).
"""

from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

from shenas_plugins.core.table import Field, Table


@dataclass
class SourceConfig(Table):
    """Base configuration for all pipes.

    Same deferred-validation pattern as ``SourceAuth`` -- ``table_name``
    is set later by ``Source.__init_subclass__`` so per-source ``Config``
    subclasses are kept abstract until
    :func:`shenas_plugins.core.base_config.finalize_pipe_table` is called.
    """

    _abstract: ClassVar[bool] = True
    table_display_name: ClassVar[str] = "Source Config"
    table_description: ClassVar[str | None] = "Per-source configuration storage."
    table_pk: ClassVar[tuple[str, ...]] = ("id",)
    table_schema: ClassVar[str | None] = "config"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        # Defer validation: see SourceAuth.__init_subclass__ for the rationale.
        if "_abstract" not in cls.__dict__:
            cls._abstract = True
        super().__init_subclass__(**kwargs)

    @classmethod
    def _config_schema(cls, schema: str | None) -> str:
        if schema is not None:
            return schema
        from app.user_context import user_schema

        return user_schema("config")

    @classmethod
    def read_row(cls, *, schema: str | None = None) -> dict[str, Any] | None:
        return super().read_row(schema=cls._config_schema(schema))

    @classmethod
    def write_row(cls, *, schema: str | None = None, **kwargs: Any) -> None:
        super().write_row(schema=cls._config_schema(schema), **kwargs)

    @classmethod
    def clear_rows(cls, *, schema: str | None = None) -> None:
        super().clear_rows(schema=cls._config_schema(schema))

    id: Annotated[int, Field(db_type="INTEGER", description="Config row identifier")] = 1
    sync_frequency: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="Sync frequency in minutes (unset = no scheduled sync)",
                ui_widget="text",
                example_value="60",
            ),
        ]
        | None
    ) = None
    lookback_period: (
        Annotated[
            int,
            Field(
                db_type="INTEGER",
                description="How far back to look on initial or full-refresh sync, in minutes (unset = pipe default)",
                ui_widget="text",
                example_value="43200",
            ),
        ]
        | None
    ) = None
