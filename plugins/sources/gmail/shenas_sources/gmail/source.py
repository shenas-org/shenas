"""Gmail source -- syncs email metadata via Google OAuth2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_auth import SourceAuth
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class GmailSource(Source):
    name = "gmail"
    display_name = "Gmail"
    primary_table = "messages"
    description = (
        "Syncs email metadata from Gmail.\n\n"
        "Uses Google OAuth2 with shared credentials from shenas-source-core. "
        "Authorization URL is passed back to the CLI for browser-based consent."
    )

    @dataclass
    class Auth(SourceAuth):
        token: (
            Annotated[
                str | None,
                Field(db_type="VARCHAR", description="Google OAuth2 credentials (JSON)", category="secret"),
            ]
            | None
        ) = None

    @dataclass
    class Config(SourceConfig):
        lookback_period: Annotated[
            int | None,
            Field(
                db_type="INTEGER",
                description="How many days back to fetch (unset = all mail)",
                ui_widget="text",
                example_value="90",
            ),
        ] = None

    @property
    def auth_fields(self) -> list:  # No user input -- browser OAuth
        return []

    auth_instructions = "Click Authenticate to sign in with your Google account."

    def _google_auth(self) -> Any:
        from shenas_sources.core.google_auth import GoogleAuth

        return GoogleAuth(
            "gmail",
            ["https://www.googleapis.com/auth/gmail.readonly"],
            "gmail",
            "v1",
            auth_cls=self.Auth,
        )

    def build_client(self) -> Any:
        return self._google_auth().build_client()

    @property
    def supports_oauth_redirect(self) -> bool:
        return True

    def start_oauth(self, redirect_uri: str, credentials: dict[str, str] | None = None) -> str:  # noqa: ARG002
        return self._google_auth().start_oauth(redirect_uri)

    def complete_oauth(self, *, code: str, state: str | None = None) -> None:
        self._google_auth().complete_oauth(code, state)

    def sync(self, *, full_refresh: bool = False, **_kwargs: Any) -> None:
        """Custom sync: page-by-page flush for large mailboxes."""
        import dlt
        from opentelemetry import trace

        from shenas_sources.core.cli import print_load_info
        from shenas_sources.core.db import DB_PATH, dlt_destination, flush_to_encrypted
        from shenas_sources.gmail.tables import Labels, message_pages

        tracer = trace.get_tracer("shenas.sources")
        service = self.build_client()
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        self.log.info("Sync started: gmail (dataset=gmail, full_refresh=%s)", full_refresh)

        with tracer.start_as_current_span("source.sync", attributes={"source.name": "gmail"}):
            page_num = 0
            total_msgs = 0

            query = self._gmail_lookback_query()
            if query:
                self.log.info("Gmail lookback query: %s", query)
            for page in message_pages(service, query=query):
                page_num += 1

                with tracer.start_as_current_span("source.fetch", attributes={"resource": "messages", "page": page_num}):
                    dest, mem_con = dlt_destination()
                    pipeline = dlt.pipeline(pipeline_name="gmail", destination=dest, dataset_name="gmail")

                    @dlt.resource(name="messages", write_disposition="merge", primary_key="id")
                    def _page_data(_data: tuple[dict[str, Any], ...] = tuple(page)) -> Any:
                        yield from _data

                    ref = "drop_sources" if full_refresh and page_num == 1 else None
                    load_info = pipeline.run(_page_data(), refresh=ref)  # ty: ignore[invalid-argument-type]
                    print_load_info(load_info)

                with tracer.start_as_current_span("source.flush", attributes={"resource": "messages", "page": page_num}):
                    flush_to_encrypted(mem_con, "gmail")
                    total_msgs += len(page)
                    self.log.info("Flushed page %d (%d messages, %d total)", page_num, len(page), total_msgs)

            # Sync labels (small, single pass)
            with tracer.start_as_current_span("source.fetch", attributes={"resource": "labels"}):
                dest, mem_con = dlt_destination()
                pipeline = dlt.pipeline(pipeline_name="gmail", destination=dest, dataset_name="gmail")
                load_info = pipeline.run(Labels.to_resource(service))
                print_load_info(load_info)

            with tracer.start_as_current_span("source.flush", attributes={"resource": "labels"}):
                flush_to_encrypted(mem_con, "gmail")

            self.log.info("Sync complete: gmail (%d messages in %d pages)", total_msgs, page_num)

    def _gmail_lookback_query(self) -> str:
        """Build a Gmail search query from the lookback_period config."""
        try:
            row = self.Config.read_row()  # ty: ignore[unresolved-attribute]
            val = getattr(row, "lookback_period", None) if row else None
            if val is not None and int(val) > 0:
                return f"newer_than:{int(val)}d"
        except Exception:
            pass
        return ""

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.gmail.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
