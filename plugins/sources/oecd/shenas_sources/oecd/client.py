"""OECD SDMX REST API client.

Uses the new API at https://sdmx.oecd.org/public/rest/.
No authentication required. Parses SDMX-JSON responses.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

BASE_URL = "https://sdmx.oecd.org/public/rest"

# Dataset configurations: (agency, dataflow_id, key_template, measure_description)
# key_template uses {countries} placeholder for the REF_AREA dimension
DATASETS: dict[str, dict[str, str]] = {
    "gdp": {
        "agency": "OECD.SDD.NAD",
        "dataflow": "DSD_NAMAIN1@DF_TABLE1_EXPENDITURE_HRES",
        "key": "A.{countries}.B1GQ.........V.USD_PPP.PS..",
        "name": "GDP (USD PPP)",
    },
    "unemployment": {
        "agency": "OECD.SDD.TPS",
        "dataflow": "DSD_LFS@DF_IALFS_UNE_Q",
        "key": "Q.{countries}......UNE_LF_M",
        "name": "Unemployment rate (%)",
    },
    "cpi": {
        "agency": "OECD.SDD.TPS",
        "dataflow": "DSD_PRICES@DF_PRICES_ALL",
        "key": "A.{countries}......CPI..",
        "name": "Consumer Price Index",
    },
}


class OECDClient:
    """HTTP client for the OECD SDMX REST API."""

    def __init__(self, country_codes: list[str] | None = None) -> None:
        self.country_codes = country_codes
        self._http = httpx.Client(timeout=180.0)

    def close(self) -> None:
        self._http.close()

    def _fetch_sdmx(
        self,
        agency: str,
        dataflow: str,
        key: str,
        start_period: str = "2000",
    ) -> dict[str, Any]:
        """Fetch SDMX-JSON data from the OECD API."""
        countries = "+".join(self.country_codes) if self.country_codes else ""
        resolved_key = key.format(countries=countries)

        url = f"{BASE_URL}/data/{agency},{dataflow}/{resolved_key}"
        params = {
            "startPeriod": start_period,
            "format": "jsondata",
            "detail": "dataonly",
            "dimensionAtObservation": "AllDimensions",
        }

        resp = self._http.get(url, params=params)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "10"))
            time.sleep(retry_after)
            resp = self._http.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _parse_sdmx_flat(
        self,
        data: dict[str, Any],
        indicator_name: str,
    ) -> list[dict[str, Any]]:
        """Parse SDMX-JSON with dimensionAtObservation=AllDimensions."""
        structure = data.get("data", {}).get("structure", {})
        dimensions = structure.get("dimensions", {})
        obs_dims = dimensions.get("observation", [])

        # Build dimension value lookups
        dim_values: list[list[dict[str, str]]] = []
        dim_names: list[str] = []
        for dim in obs_dims:
            dim_names.append(dim.get("id", ""))
            dim_values.append(dim.get("values", []))

        # Find key dimension positions
        ref_area_pos = _find_dim_pos(dim_names, "REF_AREA")
        time_pos = _find_dim_pos(dim_names, "TIME_PERIOD")

        datasets = data.get("data", {}).get("dataSets", [])
        rows: list[dict[str, Any]] = []

        for ds in datasets:
            observations = ds.get("observations", {})
            for obs_key, obs_val in observations.items():
                indices = [int(x) for x in obs_key.split(":")]
                value = obs_val[0] if obs_val else None
                if value is None:
                    continue

                country = ""
                period = ""
                if ref_area_pos is not None and ref_area_pos < len(indices):
                    idx = indices[ref_area_pos]
                    if idx < len(dim_values[ref_area_pos]):
                        country = dim_values[ref_area_pos][idx].get("id", "")
                if time_pos is not None and time_pos < len(indices):
                    idx = indices[time_pos]
                    if idx < len(dim_values[time_pos]):
                        period = dim_values[time_pos][idx].get("id", "")

                rows.append(
                    {
                        "country_code": country,
                        "indicator_name": indicator_name,
                        "period": period,
                        "value": float(value),
                    }
                )

        return rows

    def get_dataset(self, dataset_key: str) -> list[dict[str, Any]]:
        """Fetch and parse a predefined OECD dataset."""
        cfg = DATASETS[dataset_key]
        data = self._fetch_sdmx(
            agency=cfg["agency"],
            dataflow=cfg["dataflow"],
            key=cfg["key"],
        )
        return self._parse_sdmx_flat(data, indicator_name=cfg["name"])


def _find_dim_pos(dim_names: list[str], target: str) -> int | None:
    """Find the position of a dimension by name."""
    for i, name in enumerate(dim_names):
        if name == target:
            return i
    return None
