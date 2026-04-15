"""Eurostat source -- city-level demographics and economics from the Urban Audit.

No authentication required. Configure one or more Urban Audit city codes
(e.g. DE004C for Berlin, FR001C for Paris) in the Config tab.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from app.table import Field
from shenas_sources.core.base_config import SourceConfig
from shenas_sources.core.source import Source


class EurostatSource(Source):
    name = "eurostat"
    display_name = "Eurostat"
    primary_table = "city_population"
    description = (
        "City-level demographics and economics from Eurostat Urban Audit.\n\n"
        "Covers ~900 European cities with population, labour market, GDP, "
        "and living condition indicators. No API key required.\n\n"
        "Set Urban Audit city codes in the Config tab (e.g. DE004C for Berlin)."
    )

    @dataclass
    class Config(SourceConfig):
        city_codes: Annotated[
            str | None,
            Field(
                db_type="VARCHAR",
                description="Comma-separated Urban Audit city codes (e.g. DE004C,FR001C,SE001C)",
            ),
        ] = None

    def build_client(self) -> Any:
        from shenas_sources.eurostat.client import EurostatClient

        cfg = self.Config.read_row()
        if not cfg or not cfg.get("city_codes"):
            msg = "Set city codes in the Config tab (e.g. DE004C,FR001C)."
            raise RuntimeError(msg)
        codes = [c.strip() for c in cfg["city_codes"].split(",") if c.strip()]
        return EurostatClient(city_codes=codes)

    def resources(self, client: Any) -> list[Any]:
        from shenas_sources.eurostat.tables import TABLES

        return [t.to_resource(client) for t in TABLES]
