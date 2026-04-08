"""Dataset plugin ABC."""

from __future__ import annotations

from typing import Any, ClassVar

from shenas_plugins.core.plugin import Plugin


class Dataset(Plugin):
    """Canonical metrics schema."""

    _kind = "dataset"
    has_data = True
    all_tables: ClassVar[list[type]]
    primary_table: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if hasattr(cls, "all_tables"):
            cls.tables = [t.table_name for t in cls.all_tables]

    def get_info(self) -> dict[str, Any]:
        info = super().get_info()
        info["primary_table"] = self.primary_table
        return info

    @classmethod
    def ensure(cls, con: Any) -> None:
        from shenas_plugins.core.ddl import ensure_schema

        ensure_schema(con, all_tables=cls.all_tables)

    @classmethod
    def ensure_all(cls, con: Any) -> None:
        """Ensure all installed dataset plugins have their tables created."""
        from app.api.sources import _load_datasets

        for dataset_cls in _load_datasets():
            dataset_cls.ensure(con)

    @classmethod
    def metadata(cls) -> list[dict[str, Any]]:
        from shenas_plugins.core.introspect import schema_metadata

        return schema_metadata(all_tables=cls.all_tables)
