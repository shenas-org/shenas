"""Google Calendar OAuth2 -- delegates to shared GoogleAuth."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, ClassVar

from shenas_pipes.core.base_auth import PipeAuth
from shenas_pipes.core.google_auth import GoogleAuth
from shenas_schemas.core.field import Field


@dataclass
class GCalendarAuth(PipeAuth):
    """Google Calendar authentication credentials."""

    __table__: ClassVar[str] = "pipe_gcalendar"

    token: Annotated[
        str | None, Field(db_type="VARCHAR", description="Google OAuth2 credentials (JSON)", category="secret")
    ] = None


_auth = GoogleAuth(
    "gcalendar", ["https://www.googleapis.com/auth/calendar.readonly"], "calendar", "v3", auth_cls=GCalendarAuth
)

AUTH_FIELDS = _auth.AUTH_FIELDS
AUTH_INSTRUCTIONS = _auth.AUTH_INSTRUCTIONS
build_client = _auth.build_client
authenticate = _auth.authenticate
