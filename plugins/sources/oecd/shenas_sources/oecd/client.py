"""OECD SDMX REST API client.

Uses the public SDMX 2.1 REST API at ``https://sdmx.oecd.org/public/rest``.
No authentication required. Parses SDMX-JSON 2.0 responses.

All three default indicators are exposed by the **Key Economic Indicators**
dataflow (``OECD.SDD.STES:DSD_KEI@DF_KEI`` v4.0), so the client can use a
single dataflow with different MEASURE codes rather than juggling stale
NAMAIN/LFS/PRICES dataflow IDs that the OECD has since renamed.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

BASE_URL = "https://sdmx.oecd.org/public/rest"

# All three indicators currently come from the same KEI dataflow.
# Shape of the SDMX key: REF_AREA.FREQ.MEASURE.UNIT_MEASURE.ACTIVITY.ADJUSTMENT.TRANSFORMATION
# (7 dimensions; TIME_PERIOD is queried via startPeriod). Empty values are wildcards.
KEI_AGENCY = "OECD.SDD.STES"
KEI_DATAFLOW = "DSD_KEI@DF_KEI"
KEI_VERSION = "4.0"
KEI_FREQ = "A"  # annual
KEI_KEY_TEMPLATE = "{countries}." + KEI_FREQ + ".{measure}...."

DATASETS: dict[str, dict[str, str]] = {
    "gdp": {"measure": "B1GQ_Q", "name": "GDP (volume)"},
    "unemployment": {"measure": "UNEMP", "name": "Unemployment rate"},
    "cpi": {"measure": "CP", "name": "Consumer prices"},
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
        measure: str,
        start_period: str = "2000",
    ) -> dict[str, Any]:
        """Fetch SDMX-JSON data from the OECD KEI dataflow."""
        countries = "+".join(self.country_codes) if self.country_codes else ""
        key = KEI_KEY_TEMPLATE.format(countries=countries, measure=measure)

        url = f"{BASE_URL}/data/{KEI_AGENCY},{KEI_DATAFLOW},{KEI_VERSION}/{key}"
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
        """Parse SDMX-JSON 2.0 with dimensionAtObservation=AllDimensions."""
        # SDMX-JSON 2.0 puts dimensions under data.structures[0]; older responses
        # used data.structure (singular). Accept both for resilience.
        structures = data.get("data", {}).get("structures") or []
        structure = structures[0] if structures else data.get("data", {}).get("structure", {})
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
                # SDMX-JSON 2.0 uses ":" as the dimension index separator.
                indices = [int(x) if x.isdigit() else 0 for x in obs_key.split(":")]
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
        """Fetch and parse one of the predefined OECD KEI indicators."""
        cfg = DATASETS[dataset_key]
        data = self._fetch_sdmx(measure=cfg["measure"])
        return self._parse_sdmx_flat(data, indicator_name=cfg["name"])


def _find_dim_pos(dim_names: list[str], target: str) -> int | None:
    """Find the position of a dimension by name."""
    for i, name in enumerate(dim_names):
        if name == target:
            return i
    return None
