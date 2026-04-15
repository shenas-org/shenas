"""Numbeo source -- cost-of-living and quality-of-life city indices."""

from __future__ import annotations

from typing import Any

from shenas_sources.core.source import Source


class NumbeoSource(Source):
    name = "numbeo"
    display_name = "Numbeo"
    primary_table = "city_indices"
    description = "Cost-of-living and quality-of-life indices for cities worldwide from Numbeo."

    def build_client(self) -> Any:
        raise NotImplementedError

    def resources(self, client: Any) -> list[Any]:
        raise NotImplementedError
