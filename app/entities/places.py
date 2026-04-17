"""Place-entity view for geo-aware source plugins.

:class:`PlacesWide` is a :class:`~app.table.View` that JOINs
``shenas_system.entities`` with ``latitude``, ``longitude``, and
``radius_m`` statements to produce one row per place entity with typed
coordinate columns. Source plugins (openmeteo, openaq) query it via the
standard ORM (``PlacesWide.all(where=...)``) instead of writing raw EAV
join SQL.

:func:`ensure_places_wide_view` creates (or replaces) the underlying
DuckDB VIEW. It is called from :func:`app.entity.ensure_all_wide_views`
at bootstrap and after every sync so the view always reflects the
current statement set.
"""

from __future__ import annotations

from typing import Annotated

from app.table import Field, View


class PlacesWide(View):
    """Pre-pivoted view of place entities with coordinates.

    Reads from ``shenas_system.entities`` filtered to place types
    (city, residence, country) and joins ``shenas_system.statements``
    for ``latitude``, ``longitude``, and optional ``radius_m``.
    """

    class _Meta:
        name = "places_wide"
        display_name = "Places (wide)"
        schema = "shenas_system"
        pk = ("entity_id",)

    entity_id: Annotated[
        str,
        Field(db_type="VARCHAR", description="Entity UUID"),
    ] = ""
    name: Annotated[
        str,
        Field(db_type="VARCHAR", description="Display name"),
    ] = ""
    entity_type: Annotated[
        str,
        Field(db_type="VARCHAR", description="Entity type (city, residence, country)"),
    ] = ""
    latitude: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Latitude in decimal degrees"),
    ] = None
    longitude: Annotated[
        float | None,
        Field(db_type="DOUBLE", description="Longitude in decimal degrees"),
    ] = None
    radius_m: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Search radius in meters (optional)"),
    ] = None

    @classmethod
    def _view_sql(cls) -> str:
        return """
        SELECT e.uuid AS entity_id,
               e.name,
               e.type AS entity_type,
               TRY_CAST(lat.value AS DOUBLE) AS latitude,
               TRY_CAST(lng.value AS DOUBLE) AS longitude,
               TRY_CAST(rad.value AS INTEGER) AS radius_m
        FROM shenas_system.entities e
        JOIN shenas_system.statements lat
          ON lat.entity_id = e.uuid
         AND lat.property_id = 'latitude'
         AND lat._dlt_valid_to IS NULL
        JOIN shenas_system.statements lng
          ON lng.entity_id = e.uuid
         AND lng.property_id = 'longitude'
         AND lng._dlt_valid_to IS NULL
        LEFT JOIN shenas_system.statements rad
          ON rad.entity_id = e.uuid
         AND rad.property_id = 'radius_m'
         AND rad._dlt_valid_to IS NULL
        WHERE e.type IN ('city', 'residence', 'country')
        """


__all__ = ["PlacesWide"]
