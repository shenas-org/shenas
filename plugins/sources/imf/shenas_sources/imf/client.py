"""IMF DataMapper API client.

Uses the DataMapper API at https://www.imf.org/external/datamapper/api/v1/.
No authentication required.
"""

from __future__ import annotations

from typing import Any

import httpx

BASE_URL = "https://www.imf.org/external/datamapper/api/v1"

# Core WEO indicators
WEO_INDICATORS = {
    "NGDP_RPCH": "GDP growth (annual %)",
    "NGDPD": "GDP (current USD, billions)",
    "NGDPDPC": "GDP per capita (current USD)",
    "PCPIPCH": "Inflation, CPI (annual %)",
    "LUR": "Unemployment rate (%)",
    "BCA_NGDPD": "Current account balance (% of GDP)",
    "GGXWDG_NGDP": "Government gross debt (% of GDP)",
    "GGXCNL_NGDP": "Government net lending/borrowing (% of GDP)",
    "NGAP_NPGDP": "Output gap (% of potential GDP)",
    "GGR_NGDP": "Government revenue (% of GDP)",
    "GGX_NGDP": "Government expenditure (% of GDP)",
}


class IMFClient:
    """HTTP client for the IMF DataMapper API."""

    def __init__(self, country_codes: list[str] | None = None) -> None:
        self.country_codes = country_codes
        self._http = httpx.Client(timeout=120.0)

    def close(self) -> None:
        self._http.close()

    def get_indicator(self, indicator_code: str) -> list[dict[str, Any]]:
        """Fetch data for a single WEO indicator."""
        url = f"{BASE_URL}/{indicator_code}"
        resp = self._http.get(url)
        resp.raise_for_status()
        data = resp.json()

        values = data.get("values", {}).get(indicator_code, {})

        rows: list[dict[str, Any]] = []
        for country_code, year_data in values.items():
            if self.country_codes and country_code not in self.country_codes:
                continue
            if not isinstance(year_data, dict):
                continue
            for year_str, value in year_data.items():
                if value is None:
                    continue
                rows.append(
                    {
                        "country_code": country_code,
                        "indicator_code": indicator_code,
                        "indicator_name": WEO_INDICATORS.get(indicator_code, ""),
                        "year": int(year_str),
                        "value": float(value),
                    }
                )
        return rows

    def get_countries(self) -> list[dict[str, Any]]:
        """Fetch IMF country list."""
        resp = self._http.get(f"{BASE_URL}/countries")
        resp.raise_for_status()
        data = resp.json()
        countries = data.get("countries", {})
        rows: list[dict[str, Any]] = []
        for code, info in countries.items():
            if not isinstance(info, dict):
                continue
            rows.append(
                {
                    "country_code": code,
                    "name": info.get("label", ""),
                }
            )
        return rows
