"""Urban Audit code -> Wikidata QID mapping.

Resolves Eurostat Urban Audit city codes (e.g. DE004C) to Wikidata QIDs
(e.g. Q365 for Cologne) via the chain:

    URAU code -> NUTS3 code (GISCO GeoJSON) -> QID (Wikidata P605)

The GISCO GeoJSON is downloaded once and cached. The Wikidata SPARQL
query resolves all NUTS3 codes to QIDs in a single batch.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.request import Request, urlopen

log = logging.getLogger("shenas.eurostat.urban_audit")

GISCO_URL = "https://gisco-services.ec.europa.eu/distribution/v2/urau/geojson/URAU_RG_100K_2021_3035_CITIES.geojson"

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"


def _fetch_gisco_mapping() -> dict[str, dict[str, str]]:
    """Download GISCO GeoJSON and extract {URAU_CODE: {name, nuts3}}.

    Returns a dict like::

        {"DE004C": {"name": "Koln", "nuts3": "DEA23"}, ...}
    """
    req = Request(GISCO_URL, headers={"User-Agent": "shenas/1.0"})
    with urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    mapping: dict[str, dict[str, str]] = {}
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        code = props.get("URAU_CODE", "")
        name = props.get("URAU_NAME", "")
        nuts3 = props.get("NUTS3_2021", "")
        if code and nuts3:
            mapping[code] = {"name": name, "nuts3": nuts3}
    return mapping


def _resolve_nuts3_to_qid(nuts3_codes: list[str]) -> dict[str, str]:
    """Batch-query Wikidata SPARQL to resolve NUTS3 codes to QIDs via P605.

    Returns ``{"DEA23": "Q365", "FR101": "Q90", ...}``.
    """
    if not nuts3_codes:
        return {}

    # Build VALUES clause for SPARQL
    values = " ".join(f'"{code}"' for code in nuts3_codes)
    query = f"""
    SELECT ?nuts3 ?city WHERE {{
        VALUES ?nuts3 {{ {values} }}
        ?city wdt:P605 ?nuts3 .
        ?city wdt:P31/wdt:P279* wd:Q515 .
    }}
    """

    req = Request(
        f"{WIKIDATA_SPARQL}?query={query.replace(' ', '%20').replace('{', '%7B').replace('}', '%7D')}",
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "shenas/1.0",
        },
    )
    try:
        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except Exception:
        log.warning("Wikidata SPARQL query failed, falling back to empty mapping")
        return {}

    result: dict[str, str] = {}
    for binding in data.get("results", {}).get("bindings", []):
        nuts3 = binding["nuts3"]["value"]
        qid = binding["city"]["value"].split("/")[-1]
        if nuts3 not in result:
            result[nuts3] = qid
    return result


def build_urau_to_qid(city_codes: list[str] | None = None) -> dict[str, dict[str, Any]]:
    """Build a mapping from Urban Audit codes to Wikidata QIDs.

    Returns::

        {
            "DE004C": {"name": "Koln", "nuts3": "DEA23", "qid": "Q365"},
            "FR001C": {"name": "Paris", "nuts3": "FR101", "qid": "Q90"},
            ...
        }

    If ``city_codes`` is provided, only those codes are included.
    Otherwise all cities from the GISCO dataset are mapped.
    """
    log.info("Fetching GISCO Urban Audit -> NUTS3 mapping...")
    gisco = _fetch_gisco_mapping()

    if city_codes:
        gisco = {k: v for k, v in gisco.items() if k in set(city_codes)}

    # Collect unique NUTS3 codes to resolve
    nuts3_codes = sorted({entry["nuts3"] for entry in gisco.values() if entry["nuts3"]})

    log.info("Resolving %d NUTS3 codes to Wikidata QIDs...", len(nuts3_codes))
    nuts3_to_qid = _resolve_nuts3_to_qid(nuts3_codes)

    # Merge
    result: dict[str, dict[str, Any]] = {}
    for urau_code, entry in gisco.items():
        qid = nuts3_to_qid.get(entry["nuts3"])
        result[urau_code] = {
            "name": entry["name"],
            "nuts3": entry["nuts3"],
            "qid": qid,
        }
    return result
