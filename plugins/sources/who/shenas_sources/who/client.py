"""WHO Global Health Observatory OData v4 client.

Uses the GHO API at https://ghoapi.azureedge.net/api/.
No authentication required. Responses paginated via @odata.nextLink.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import logging

import httpx

BASE_URL = "https://ghoapi.azureedge.net/api"

# Core health indicators to fetch
CORE_INDICATORS = {
    # Life expectancy
    "WHOSIS_000001": "Life expectancy at birth (years)",
    "WHOSIS_000015": "Healthy life expectancy (HALE) at birth",
    # Mortality
    "MDG_0000000007": "Under-five mortality rate (per 1000 live births)",
    "MDG_0000000003": "Infant mortality rate (per 1000 live births)",
    "WHOSIS_000004": "Neonatal mortality rate",
    "SA_0000001462": "Maternal mortality ratio (per 100000 live births)",
    "NCDMORT3070": "NCD mortality, probability of dying 30-70",
    # Vaccination
    "WHS4_100": "DTP3 immunization coverage (%)",
    "WHS8_110": "Measles (MCV1) immunization coverage (%)",
    # Healthcare spending
    "GHED_CHEGDP_SHA2011": "Health expenditure (% of GDP)",
    "GHED_CHE_pc_US_SHA2011": "Health expenditure per capita (USD)",
    "GHED_OOPSCHE_SHA2011": "Out-of-pocket expenditure (% of health exp)",
    # Health system
    "UHC_INDEX_REPORTED": "UHC Service Coverage Index",
    "HWF_0001": "Physicians density (per 10000)",
    # Risk factors
    "NCD_BMI_30C": "Obesity prevalence, BMI >= 30 (%)",
    "TOBACCO_0000000192": "Tobacco smoking prevalence (%)",
    "NCD_GLUC_04": "Diabetes prevalence (%)",
    # Environment
    "SDGPM25": "Mean annual PM2.5 concentration",
    "WSH_SANITATION_SAFELY_MANAGED": "Safely managed sanitation (%)",
    "WSH_WATER_SAFELY_MANAGED": "Safely managed drinking water (%)",
    # Disease
    "HIV_0000000001": "HIV prevalence, adults 15-49 (%)",
    "MORT_100": "Tuberculosis mortality rate (per 100000)",
}


class WHOClient:
    """HTTP client for the WHO GHO OData API."""

    def __init__(self, country_codes: list[str] | None = None, *, log: logging.Logger) -> None:
        self.country_codes = country_codes
        self.log = log
        self._http = httpx.Client(timeout=120.0)

    def close(self) -> None:
        self._http.close()

    def _get_all_pages(self, url: str) -> list[dict[str, Any]]:
        """Fetch all pages following @odata.nextLink."""
        results: list[dict[str, Any]] = []
        while url:
            resp = self._http.get(url)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("value", []))
            url = data.get("@odata.nextLink", "")
        return results

    def get_indicator(self, indicator_code: str) -> list[dict[str, Any]]:
        """Fetch data for a single indicator, optionally filtered by country.

        Returns an empty list if the indicator has been renamed or removed
        upstream (HTTP 404), logging a warning. One dead indicator code
        would otherwise abort the entire sync.
        """
        filters = []
        if self.country_codes:
            country_filter = " or ".join(f"SpatialDim eq '{c}'" for c in self.country_codes)
            filters.append(f"({country_filter})")
        # Only keep "both sexes" aggregate when a sex dimension is present.
        # The GHO API uses 'SEX_BTSX' (not the bare 'BTSX' the docs sometimes
        # quote); accept both plus null (indicators with no sex dimension).
        filters.append("(Dim1 eq 'SEX_BTSX' or Dim1 eq 'BTSX' or Dim1 eq null)")

        url = f"{BASE_URL}/{indicator_code}"
        if filters:
            url += "?$filter=" + " and ".join(filters)

        try:
            raw = self._get_all_pages(url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                self.log.warning("WHO indicator %s not found (404); skipping", indicator_code)
                return []
            raise
        rows: list[dict[str, Any]] = []
        for item in raw:
            numeric_val = item.get("NumericValue")
            if numeric_val is None:
                continue
            rows.append(
                {
                    "country_code": item.get("SpatialDim", ""),
                    "indicator_code": indicator_code,
                    "indicator_name": CORE_INDICATORS.get(indicator_code, ""),
                    "year": item.get("TimeDim"),
                    "value": float(numeric_val),
                    "value_low": item.get("Low"),
                    "value_high": item.get("High"),
                }
            )
        return rows
