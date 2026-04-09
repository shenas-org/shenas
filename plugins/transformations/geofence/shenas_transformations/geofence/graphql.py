"""GraphQL extension for geofence CRUD.

Discovered via the ``shenas.graphql`` entry point. Provides
``QueryMixin`` and ``MutationMixin`` that are composed into the
schema at startup.
"""

from __future__ import annotations

import strawberry

from app.graphql.types import GeofenceCreateInput, GeofenceType, GeofenceUpdateInput, OkType


def _geofence_to_gql(g: object) -> GeofenceType:
    return GeofenceType(
        id=g.id,  # type: ignore[attr-defined]
        name=g.name,  # type: ignore[attr-defined]
        latitude=g.latitude,  # type: ignore[attr-defined]
        longitude=g.longitude,  # type: ignore[attr-defined]
        radius_m=g.radius_m,  # type: ignore[attr-defined]
        category=g.category or "",  # type: ignore[attr-defined]
        added_at=g.added_at,  # type: ignore[attr-defined]
        updated_at=g.updated_at,  # type: ignore[attr-defined]
    )


class QueryMixin:
    @strawberry.field
    def geofences(self) -> list[GeofenceType]:
        from app.geofences import Geofence

        return [_geofence_to_gql(g) for g in Geofence.all(order_by="name")]

    @strawberry.field
    def geofence(self, geofence_id: int) -> GeofenceType | None:
        from app.geofences import Geofence

        g = Geofence.find(geofence_id)
        return _geofence_to_gql(g) if g else None


class MutationMixin:
    @strawberry.mutation
    def create_geofence(self, geofence_input: GeofenceCreateInput) -> GeofenceType:
        from app.geofences import Geofence

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
        from app.geofences import Geofence

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
        from app.geofences import Geofence
        from app.models import OkResponse

        g = Geofence.find(geofence_id)
        if g:
            g.delete()
        return OkType.from_pydantic(OkResponse(ok=True))
