"""Google Photos OAuth2 -- delegates to shared GoogleAuth."""

from shenas_pipes.core.google_auth import GoogleAuth

_auth = GoogleAuth(
    "gphotos",
    ["https://www.googleapis.com/auth/photoslibrary.readonly"],
    "photoslibrary",
    "v1",
    static_discovery=False,
)

AUTH_FIELDS = _auth.AUTH_FIELDS
build_client = _auth.build_client
authenticate = _auth.authenticate
