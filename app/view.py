"""View: read-only DuckDB VIEW with ORM access.

Concrete subclasses override :meth:`_view_sql` to return the SELECT
statement the view wraps. :meth:`ensure` creates the view via
``CREATE OR REPLACE VIEW``. Write operations are not available --
Views inherit only the read-only API from :class:`~app.relation.Relation`.

For views whose column set is known at import time, declare a static
subclass. For views whose columns are discovered at runtime (e.g.
per-EntityType wide views), use :meth:`View.build` to generate a
dynamic subclass with full ORM access.
"""

from __future__ import annotations

import dataclasses
from typing import Any, ClassVar

from app.relation import DataRelation, Field, Relation


class View(Relation):
    """A DuckDB VIEW with typed, read-only ORM access.

    ``pk`` is optional -- declare it when ``find()`` makes sense,
    omit it when the view has no natural key.
    """

    _abstract: ClassVar[bool] = True

    @classmethod
    def _view_sql(cls) -> str:
        """Return the SELECT statement this view wraps. Subclasses must override."""
        msg = f"{cls.__name__}._view_sql() not implemented"
        raise NotImplementedError(msg)

    @classmethod
    def ensure(cls, *, schema: str | None = None) -> None:
        """Create or replace this view in the given schema.

        Uses the cursor system from :mod:`app.database`.
        """
        import logging

        from app.database import cursor

        s = schema or getattr(cls._Meta, "schema", None)
        if s is None:
            msg = f"{cls.__name__}: View.ensure() requires an explicit schema (set _Meta.schema or pass schema=)"
            raise ValueError(msg)
        sql = f'CREATE OR REPLACE VIEW "{s}"."{cls._Meta.name}" AS {cls._view_sql()}'
        with cursor(database=cls._resolve_database()) as cur:
            try:
                cur.execute(sql)
            except Exception:
                # View SQL may reference SCD2 columns (_dlt_valid_to) that
                # don't exist before the first dlt sync. Log and skip --
                # the view will be created on the next post-sync call.
                logging.getLogger("shenas.view").debug("View %s.%s deferred (likely missing SCD2 columns)", s, cls._Meta.name)

    @classmethod
    def build(
        cls,
        *,
        name: str,
        display_name: str,
        schema: str = "entities",
        sql: str,
        columns: list[tuple[str, str]],
        pk: tuple[str, ...] = (),
    ) -> type[View]:
        """Dynamically create a View subclass with typed fields and ORM access.

        Parameters
        ----------
        name : str
            DuckDB view name (e.g. ``"humans_wide"``).
        display_name : str
            Human-readable label.
        schema : str
            DuckDB schema (default ``"entities"``).
        sql : str
            The SELECT statement the view wraps.
        columns : list of (column_name, description) tuples
            Each becomes a ``str | None`` field on the dataclass.
            Fixed columns (``entity_id``, ``name``) are prepended
            automatically.
        pk : tuple of str
            Optional primary key columns for ``find()`` support.

        Returns
        -------
        type[View]
            A concrete View subclass with ``all()``, ``find()``,
            ``from_row()``, and ``ensure()`` support.

        Example
        -------
        ::

            HumansWide = View.build(
                name="humans_wide",
                display_name="Humans (wide)",
                sql="SELECT ... FROM ... GROUP BY ...",
                columns=[("sex_or_gender", "P21"), ("date_of_birth", "P569")],
                pk=("entity_id",),
            )
            HumansWide.ensure()
            rows = HumansWide.all(where="date_of_birth IS NOT NULL")
        """
        from typing import Annotated

        _sql = sql

        fields: list[Any] = [
            ("entity_id", Annotated[str, Field(db_type="VARCHAR", description="Entity UUID")], dataclasses.field(default="")),
            ("name", Annotated[str, Field(db_type="VARCHAR", description="Display name")], dataclasses.field(default="")),
        ]
        for col_name, col_desc in columns:
            fields.append(
                (
                    col_name,
                    Annotated[str | None, Field(db_type="VARCHAR", description=col_desc)],
                    dataclasses.field(default=None),
                )
            )

        view_cls = dataclasses.make_dataclass(
            name.title().replace("_", ""),
            fields,
            bases=(View,),
            namespace={
                "_view_sql": classmethod(lambda cls: _sql),  # noqa: ARG005
                "_Meta": type(
                    "_Meta",
                    (View._Meta,),
                    {
                        "name": name,
                        "display_name": display_name,
                        "schema": schema,
                        "pk": pk,
                    },
                ),
            },
        )
        view_cls._abstract = False  # ty: ignore[unresolved-attribute]
        return view_cls  # type: ignore[return-value]  # ty: ignore[invalid-return-type]


class DataView(View, DataRelation):
    """A View with metadata for UI exposure.

    Combines View (CREATE OR REPLACE VIEW, read-only) with DataRelation
    (metadata(), kind()). Use for derived views like TileInfo that should
    appear in the Data tab and support entity projection.
    """

    _abstract: ClassVar[bool] = True
