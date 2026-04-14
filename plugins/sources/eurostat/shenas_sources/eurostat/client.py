"""Eurostat JSON API client.

Uses the dissemination statistics API (JSON-stat 2.0 responses).
No authentication required.
"""

from __future__ import annotations

from typing import Any

import httpx

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

# Dataset codes for Urban Audit city-level data
DATASETS = {
    "population": "urb_cpopstr",
    "labour": "urb_clma",
    "economy": "urb_cecfi",
    "living": "urb_clivcon",
    "environment": "urb_cenv",
    "transport": "urb_ctran",
    "education": "urb_ceduc",
    "health": "urb_chlth",
}

# NUTS-3 GDP dataset
GDP_DATASET = "nama_10r_3gdp"


class EurostatClient:
    """HTTP client for the Eurostat Statistics API."""

    def __init__(self, city_codes: list[str]) -> None:
        self.city_codes = city_codes
        self._http = httpx.Client(timeout=120.0)

    def close(self) -> None:
        self._http.close()

    def _fetch_dataset(
        self,
        dataset_code: str,
        geo_codes: list[str],
        extra_params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Fetch a dataset from the Eurostat API."""
        params: dict[str, str] = {
            "geo": ",".join(geo_codes),
            "format": "JSON",
            "lang": "EN",
        }
        if extra_params:
            params.update(extra_params)
        resp = self._http.get(f"{BASE_URL}/{dataset_code}", params=params)
        resp.raise_for_status()
        return resp.json()

    def _parse_jsonstat(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse a JSON-stat 2.0 response into flat row dicts.

        Each row contains one value plus its dimension labels.
        """
        dims = data.get("id", [])
        sizes = data.get("size", [])
        values = data.get("value", {})
        dimension_info = data.get("dimension", {})

        # Build label lookups per dimension
        labels: dict[str, dict[int, str]] = {}
        codes: dict[str, dict[int, str]] = {}
        for dim_name in dims:
            dim = dimension_info.get(dim_name, {})
            cat = dim.get("category", {})
            idx = cat.get("index", {})
            lbl = cat.get("label", {})
            # index can be {code: position} or [code, ...]
            pos_to_code = {v: k for k, v in idx.items()} if isinstance(idx, dict) else dict(enumerate(idx))
            codes[dim_name] = pos_to_code
            labels[dim_name] = {pos: lbl.get(code, code) for pos, code in pos_to_code.items()}

        # Iterate over the flat value array
        rows: list[dict[str, Any]] = []
        if isinstance(values, dict):
            # Sparse format: {"0": 123, "5": 456, ...}
            for flat_idx_str, val in values.items():
                flat_idx = int(flat_idx_str)
                row = self._unflatten(flat_idx, dims, sizes, codes, labels)
                row["value"] = val
                rows.append(row)
        elif isinstance(values, list):
            # Dense format
            for flat_idx, val in enumerate(values):
                if val is None:
                    continue
                row = self._unflatten(flat_idx, dims, sizes, codes, labels)
                row["value"] = val
                rows.append(row)
        return rows

    def _unflatten(
        self,
        flat_idx: int,
        dims: list[str],
        sizes: list[int],
        codes: dict[str, dict[int, str]],
        labels: dict[str, dict[int, str]],
    ) -> dict[str, Any]:
        """Convert a flat index back to dimension code/label pairs."""
        row: dict[str, Any] = {}
        remaining = flat_idx
        for i in range(len(dims) - 1, -1, -1):
            pos = remaining % sizes[i]
            remaining //= sizes[i]
            dim_name = dims[i]
            row[f"{dim_name}_code"] = codes[dim_name].get(pos, str(pos))
            row[f"{dim_name}_label"] = labels[dim_name].get(pos, str(pos))
        return row

    def get_population(self) -> list[dict[str, Any]]:
        """Fetch city population data (total population, by broad age group)."""
        data = self._fetch_dataset(
            DATASETS["population"],
            self.city_codes,
            {"indic_ur": "DE1001V"},  # Total population
        )
        return self._parse_jsonstat(data)

    def get_labour_market(self) -> list[dict[str, Any]]:
        """Fetch city labour market indicators."""
        data = self._fetch_dataset(
            DATASETS["labour"],
            self.city_codes,
            # Unemployment rate + activity rate + employment rate
            {"indic_ur": "EC1001V,EC1002V,EC1003V,EC2020V,EC3040V"},
        )
        return self._parse_jsonstat(data)

    def get_economy(self) -> list[dict[str, Any]]:
        """Fetch city economic/financial indicators."""
        data = self._fetch_dataset(
            DATASETS["economy"],
            self.city_codes,
        )
        return self._parse_jsonstat(data)

    def get_living_conditions(self) -> list[dict[str, Any]]:
        """Fetch city living condition indicators."""
        data = self._fetch_dataset(
            DATASETS["living"],
            self.city_codes,
        )
        return self._parse_jsonstat(data)

    def get_environment(self) -> list[dict[str, Any]]:
        """Fetch city environmental indicators."""
        data = self._fetch_dataset(
            DATASETS["environment"],
            self.city_codes,
        )
        return self._parse_jsonstat(data)

    def get_gdp_nuts3(self, nuts3_codes: list[str]) -> list[dict[str, Any]]:
        """Fetch GDP at NUTS-3 level."""
        data = self._fetch_dataset(
            GDP_DATASET,
            nuts3_codes,
            {"unit": "MIO_EUR"},
        )
        return self._parse_jsonstat(data)
