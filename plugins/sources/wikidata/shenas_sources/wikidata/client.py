"""Wikidata Query Service (SPARQL) client.

No authentication required. The query service is rate-limited per IP;
respect the ``User-Agent`` guidance and keep queries as specific as
possible.

Docs: https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service
"""

from __future__ import annotations

from typing import Any

import httpx

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "shenas-source-wikidata/0.1 (https://shenas.net; contact@shenas.net)"


# SPARQL query that enumerates every sovereign state (P31 = Q3624078, which is
# a subclass of country Q6256) and extracts the properties declared on the
# ``country`` EntityType in ``app/entity.py``. Optionals are used so countries
# missing any single property still come back in the result set.
COUNTRIES_QUERY = """
SELECT DISTINCT ?country ?countryLabel ?countryDescription
       ?iso2 ?iso3
       ?capital ?capitalLabel
       ?population ?area
       ?currency ?currencyLabel
       ?coord
       (GROUP_CONCAT(DISTINCT ?languageLabel; separator="|") AS ?languages)
WHERE {
  ?country wdt:P31 wd:Q3624078.           # instance of: sovereign state
  FILTER NOT EXISTS { ?country wdt:P576 ?_dissolved. }  # still existing
  OPTIONAL { ?country wdt:P297 ?iso2. }
  OPTIONAL { ?country wdt:P298 ?iso3. }
  OPTIONAL { ?country wdt:P36  ?capital. }
  OPTIONAL { ?country wdt:P1082 ?population. }
  OPTIONAL { ?country wdt:P2046 ?area. }
  OPTIONAL { ?country wdt:P38  ?currency. }
  OPTIONAL { ?country wdt:P625 ?coord. }
  OPTIONAL {
    ?country wdt:P37 ?language.
    ?language rdfs:label ?languageLabel.
    FILTER(LANG(?languageLabel) = "en")
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
GROUP BY ?country ?countryLabel ?countryDescription
         ?iso2 ?iso3 ?capital ?capitalLabel
         ?population ?area ?currency ?currencyLabel ?coord
"""


class WikidataClient:
    """Thin wrapper around the Wikidata SPARQL endpoint."""

    def __init__(self) -> None:
        self._http = httpx.Client(
            timeout=120.0,
            headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
        )

    def close(self) -> None:
        self._http.close()

    def sparql(self, query: str) -> list[dict[str, Any]]:
        """Run a SPARQL SELECT and return the raw ``bindings`` list."""
        resp = self._http.get(SPARQL_ENDPOINT, params={"query": query, "format": "json"})
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", {}).get("bindings", [])

    def get_countries(self) -> list[dict[str, Any]]:
        """Return one dict per current sovereign state with wikidata properties.

        Keys match :class:`shenas_sources.wikidata.tables.Countries`' columns.
        Missing properties are ``None``; the ``languages`` field is a sorted
        pipe-separated string so SCD2 hashing is stable across syncs.
        """
        rows: list[dict[str, Any]] = []
        for b in self.sparql(COUNTRIES_QUERY):
            qid = _qid_from_uri(_val(b.get("country")))
            if not qid:
                continue
            languages = _val(b.get("languages")) or ""
            lat, lng = _parse_wkt_point(_val(b.get("coord")))
            rows.append(
                {
                    "wikidata_qid": qid,
                    "name": _val(b.get("countryLabel")) or qid,
                    "description": _val(b.get("countryDescription")),
                    "iso_alpha_2": _val(b.get("iso2")),
                    "iso_alpha_3": _val(b.get("iso3")),
                    "capital_qid": _qid_from_uri(_val(b.get("capital"))),
                    "capital_name": _val(b.get("capitalLabel")),
                    "population": _as_int(_val(b.get("population"))),
                    "area_km2": _as_float(_val(b.get("area"))),
                    "currency_qid": _qid_from_uri(_val(b.get("currency"))),
                    "currency_name": _val(b.get("currencyLabel")),
                    "official_languages": "|".join(sorted({s for s in languages.split("|") if s})) or None,
                    "latitude": lat,
                    "longitude": lng,
                }
            )
        return rows


def _val(binding: dict[str, Any] | None) -> str | None:
    """Pull ``value`` out of a single SPARQL result binding, or return None."""
    if not binding:
        return None
    v = binding.get("value")
    return v if isinstance(v, str) and v else None


def _qid_from_uri(uri: str | None) -> str | None:
    """http://www.wikidata.org/entity/Q183 -> Q183."""
    if not uri:
        return None
    tail = uri.rsplit("/", 1)[-1]
    return tail if tail.startswith("Q") else None


def _as_int(v: str | None) -> int | None:
    if v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _as_float(v: str | None) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_wkt_point(wkt: str | None) -> tuple[float | None, float | None]:
    """Parse a Wikidata WKT POINT literal into (latitude, longitude).

    Wikidata's P625 returns coords as ``Point(LNG LAT)`` (note the reversed
    order). Returns ``(None, None)`` on any parse failure.
    """
    if not wkt or not wkt.lower().startswith("point("):
        return None, None
    try:
        inner = wkt[wkt.index("(") + 1 : wkt.rindex(")")]
        lng_str, lat_str = inner.split()
        return float(lat_str), float(lng_str)
    except (ValueError, IndexError):
        return None, None
