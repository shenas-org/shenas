"""GraphQL extension for geofence CRUD.

Discovered via the ``shenas.graphql`` entry point. Provides
``QueryMixin`` and ``MutationMixin`` that are composed into the
schema at startup.
"""

from __future__ import annotations

import strawberry

from app.graphql.types import OkType


@strawberry.type
class GeofenceType:
    id: int
    name: str
    latitude: float
    longitude: float
    radius_m: float
    category: str
    added_at: str | None
    updated_at: str | None


@strawberry.input
class GeofenceCreateInput:
    name: str
    latitude: float
    longitude: float
    radius_m: float = 200.0
    category: str = ""


@strawberry.input
class GeofenceUpdateInput:
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_m: float | None = None
    category: str | None = None


def _geofence_to_gql(g: object) -> GeofenceType:
    return GeofenceType(
        id=g.id,  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        name=g.name,  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        latitude=g.latitude,  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        longitude=g.longitude,  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        radius_m=g.radius_m,  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        category=g.category or "",  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        added_at=g.added_at,  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        updated_at=g.updated_at,  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
    )


class QueryMixin:
    @strawberry.field
    def geofences(self) -> list[GeofenceType]:
        from shenas_transformers.geofence.model import Geofence

        return [_geofence_to_gql(g) for g in Geofence.all(order_by="name")]

    @strawberry.field
    def geofence(self, geofence_id: int) -> GeofenceType | None:
        from shenas_transformers.geofence.model import Geofence

        g = Geofence.find(geofence_id)
        return _geofence_to_gql(g) if g else None


class MutationMixin:
    @strawberry.mutation
    def create_geofence(self, geofence_input: GeofenceCreateInput) -> GeofenceType:
        from shenas_transformers.geofence.model import Geofence

        g = Geofence.create(
            name=geofence_input.name,
            latitude=geofence_input.latitude,
            longitude=geofence_input.longitude,
            radius_m=geofence_input.radius_m,
            category=geofence_input.category,
        )
        return _geofence_to_gql(g)

    @strawberry.mutation
    def update_geofence(self, geofence_id: int, geofence_input: GeofenceUpdateInput) -> GeofenceType | None:
        from shenas_transformers.geofence.model import Geofence

        g = Geofence.find(geofence_id)
        if not g:
            return None
        updated = g.update(
            name=geofence_input.name,
            latitude=geofence_input.latitude,
            longitude=geofence_input.longitude,
            radius_m=geofence_input.radius_m,
            category=geofence_input.category,
        )
        return _geofence_to_gql(updated)

    @strawberry.mutation
    def delete_geofence(self, geofence_id: int) -> OkType:
        from shenas_transformers.geofence.model import Geofence

        from app.models import OkResponse

        g = Geofence.find(geofence_id)
        if g:
            g.delete()
        return OkType.from_pydantic(OkResponse(ok=True))  # ty: ignore[unresolved-attribute]
