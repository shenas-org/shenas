"""World Bank API v2 client.

Uses the Indicators API at https://api.worldbank.org/v2/.
No authentication required. Responses paginated at 50 items per page by default.
"""

from __future__ import annotations

from typing import Any

import httpx

BASE_URL = "https://api.worldbank.org/v2"

# Core development indicators
CORE_INDICATORS = {
    # Economy
    "NY.GDP.MKTP.CD": "GDP (current USD)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "NY.GDP.PCAP.CD": "GDP per capita (current USD)",
    "NY.GDP.PCAP.PP.CD": "GDP per capita, PPP (current intl $)",
    "NY.GNP.PCAP.CD": "GNI per capita (current USD)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "SL.UEM.TOTL.ZS": "Unemployment (% of total labor force)",
    "NE.TRD.GNFS.ZS": "Trade (% of GDP)",
    "BX.KLT.DINV.WD.GD.ZS": "FDI net inflows (% of GDP)",
    "GC.DOD.TOTL.GD.ZS": "Central government debt (% of GDP)",
    # Population & demographics
    "SP.POP.TOTL": "Population, total",
    "SP.POP.GROW": "Population growth (annual %)",
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total)",
    "SP.DYN.LE00.IN": "Life expectancy at birth (years)",
    "SP.DYN.TFRT.IN": "Fertility rate (births per woman)",
    "SP.DYN.IMRT.IN": "Infant mortality rate (per 1000 live births)",
    # Education
    "SE.XPD.TOTL.GD.ZS": "Government education expenditure (% of GDP)",
    "SE.ADT.LITR.ZS": "Literacy rate, adult (% ages 15+)",
    "SE.SEC.ENRR": "School enrollment, secondary (% gross)",
    "SE.TER.ENRR": "School enrollment, tertiary (% gross)",
    # Health
    "SH.XPD.CHEX.GD.ZS": "Current health expenditure (% of GDP)",
    "SH.MED.PHYS.ZS": "Physicians (per 1000 people)",
    # Environment
    "EN.ATM.CO2E.PC": "CO2 emissions (metric tons per capita)",
    "EG.USE.PCAP.KG.OE": "Energy use (kg of oil equiv per capita)",
    "EG.FEC.RNEW.ZS": "Renewable energy consumption (% of total)",
    # Technology
    "IT.NET.USER.ZS": "Individuals using the Internet (% of population)",
    "IT.CEL.SETS.P2": "Mobile cellular subscriptions (per 100 people)",
    # Governance
    "GE.EST": "Government effectiveness (estimate)",
    "CC.EST": "Control of corruption (estimate)",
    "RL.EST": "Rule of law (estimate)",
}


class WorldBankClient:
    """HTTP client for the World Bank Indicators API v2."""

    def __init__(self, country_codes: str) -> None:
        self.country_codes = country_codes
        self._http = httpx.Client(timeout=120.0)

    def close(self) -> None:
        self._http.close()

    def _get_all_pages(
        self,
        path: str,
        params: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all pages from a World Bank API endpoint."""
        all_params = {"format": "json", "per_page": "1000"}
        if params:
            all_params.update(params)

        results: list[dict[str, Any]] = []
        page = 1
        while True:
            all_params["page"] = str(page)
            resp = self._http.get(f"{BASE_URL}/{path}", params=all_params)
            resp.raise_for_status()
            data = resp.json()
            # World Bank API returns [metadata, data] or [metadata, null]
            if not isinstance(data, list) or len(data) < 2 or data[1] is None:
                break
            results.extend(data[1])
            meta = data[0]
            total_pages = meta.get("pages", 1)
            if page >= total_pages:
                break
            page += 1
        return results

    def get_indicator(
        self,
        indicator_code: str,
        start_year: int = 1960,
        end_year: int = 2025,
    ) -> list[dict[str, Any]]:
        """Fetch a single indicator for configured countries."""
        raw = self._get_all_pages(
            f"country/{self.country_codes}/indicator/{indicator_code}",
            {"date": f"{start_year}:{end_year}"},
        )
        rows: list[dict[str, Any]] = []
        for item in raw:
            val = item.get("value")
            if val is None:
                continue
            country = item.get("country", {})
            rows.append(
                {
                    "country_code": item.get("countryiso3code", ""),
                    "country_name": country.get("value", ""),
                    "indicator_code": indicator_code,
                    "indicator_name": CORE_INDICATORS.get(indicator_code, item.get("indicator", {}).get("value", "")),
                    "year": int(item.get("date", "0")),
                    "value": float(val),
                }
            )
        return rows

    def get_countries(self) -> list[dict[str, Any]]:
        """Fetch country metadata."""
        raw = self._get_all_pages("country", {"per_page": "300"})
        return [
            {
                "country_code": item.get("iso2Code", ""),
                "country_code_iso3": item.get("id", ""),
                "name": item.get("name", ""),
                "region": item.get("region", {}).get("value", ""),
                "income_level": item.get("incomeLevel", {}).get("value", ""),
                "lending_type": item.get("lendingType", {}).get("value", ""),
                "capital_city": item.get("capitalCity", ""),
                "latitude": float(item["latitude"]) if item.get("latitude") else None,
                "longitude": float(item["longitude"]) if item.get("longitude") else None,
            }
            for item in raw
        ]
