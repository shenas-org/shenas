"""Garmin Connect pipe -- syncs health and fitness data."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

from shenas_pipes.core.pipe import Pipe
from shenas_plugins.core.base_auth import PipeAuth
from shenas_schemas.core.field import Field

_pending_mfa: dict[str, Any] = {}


class GarminPipe(Pipe):
    name = "garmin"
    display_name = "Garmin Connect"
    primary_table = "daily_stats"
    description = (
        "Syncs health and fitness data from Garmin Connect.\n\n"
        "Authenticates via email/password with MFA support. Tokens are stored "
        "in the database."
    )

    @dataclass
    class Auth(PipeAuth):
        tokens: (
            Annotated[
                str | None,
                Field(db_type="VARCHAR", description="JSON blob of garth token files", category="secret"),
            ]
            | None
        ) = None

    auth_instructions = (
        "Log in with your Garmin Connect email and password.\n"
        "If your account has MFA enabled, you will be prompted for a code."
    )

    @property
    def auth_fields(self) -> list[dict[str, str | bool]]:
        return [
            {"name": "email", "prompt": "Email", "hide": False},
            {"name": "password", "prompt": "Password", "hide": True},
        ]

    def build_client(self) -> Any:
        from garminconnect import Garmin

        row = self._auth_store.get(self.Auth)
        if row and row.get("tokens"):
            tokens = json.loads(row["tokens"])
            tmp = Path(tempfile.mkdtemp(prefix="garmin_tokens_"))
            for name, content in tokens.items():
                (tmp / name).write_text(content)
            client = Garmin()
            try:
                client.login(str(tmp))
                return client
            except Exception:
                pass

        msg = "No valid tokens found. Configure authentication in the Auth tab."
        raise RuntimeError(msg)

    def _save_tokens_from_client(self, client: Any) -> None:
        """Serialize garth tokens from client to the auth store."""
        with tempfile.TemporaryDirectory(prefix="garmin_tokens_") as tmp:
            client.client.dump(tmp)
            tokens: dict[str, str] = {}
            for f in Path(tmp).iterdir():
                if f.suffix == ".json":
                    tokens[f.name] = f.read_text()
            self._auth_store.set(self.Auth, tokens=json.dumps(tokens))

    def authenticate(self, credentials: dict[str, str]) -> None:
        from garminconnect import Garmin

        email = credentials.get("email")
        password = credentials.get("password")

        if not email or not password:
            msg = "email and password are required"
            raise ValueError(msg)

        client = Garmin(email=email, password=password, return_on_mfa=True)
        result1, result2 = client.login()

        if result1 == "needs_mfa":
            _pending_mfa["garmin"] = {"client": client, "mfa_state": result2}
            msg = "MFA code required"
            raise ValueError(msg)

        self._save_tokens_from_client(client)

    def get_pending_mfa_state(self) -> dict[str, Any] | None:
        return _pending_mfa.pop("garmin", None)

    def complete_mfa(self, state: dict[str, Any], mfa_code: str) -> None:
        client = state["client"]
        mfa_state = state["mfa_state"]
        client.resume_login(mfa_state, mfa_code)
        self._save_tokens_from_client(client)

    def resources(self, client: Any) -> list[Any]:
        from shenas_pipes.garmin.source import activities, body_composition, daily_stats, hrv, sleep, spo2

        return [
            activities(client, "30 days ago"),
            daily_stats(client, "30 days ago"),
            sleep(client, "30 days ago"),
            hrv(client, "30 days ago"),
            spo2(client, "30 days ago"),
            body_composition(client, "30 days ago"),
        ]
