"""Auth API endpoints -- handle interactive auth flows via REST."""

import importlib
import json
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthCredentials(BaseModel):
    credentials: dict[str, str] = {}


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/{pipe_name}")
def auth_pipe(pipe_name: str, body: AuthCredentials | None = None) -> StreamingResponse:
    """Run a pipe's auth flow. Credentials are passed in the request body."""
    body = body or AuthCredentials()

    def _stream() -> Iterator[str]:
        yield _sse_event("progress", {"message": f"Authenticating {pipe_name}..."})

        try:
            importlib.invalidate_caches()
            import sys

            for key in list(sys.modules):
                if key.startswith(f"shenas_pipes.{pipe_name}"):
                    del sys.modules[key]

            mod = importlib.import_module(f"shenas_pipes.{pipe_name}.auth")
        except ModuleNotFoundError as exc:
            yield _sse_event("error", {"message": f"Pipe {pipe_name} not found: {exc}"})
            return

        # Each pipe's auth module should have an authenticate(credentials) function
        # that accepts a dict of credentials and saves tokens.
        auth_fn = getattr(mod, "authenticate", None)
        if auth_fn is None:
            yield _sse_event("error", {"message": f"Pipe {pipe_name} has no authenticate() function"})
            return

        try:
            auth_fn(body.credentials)
            yield _sse_event("complete", {"message": f"Authenticated {pipe_name}"})
        except Exception as exc:
            yield _sse_event("error", {"message": str(exc)})

    return StreamingResponse(_stream(), media_type="text/event-stream")
