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

# How many entities to fetch per SPARQL request. The public endpoint
# has a 60-second query timeout; keep batches small to stay under it.
BATCH_SIZE = 50

# How many instances to seed per type.
SEED_LIMIT = 100


class WikidataClient:
    """Thin wrapper around the Wikidata SPARQL endpoint."""

    def __init__(self) -> None:
        self._http = httpx.Client(
            timeout=httpx.Timeout(connect=10.0, read=65.0, write=10.0, pool=10.0),
            headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
        )

    def close(self) -> None:
        self._http.close()

    def sparql(self, query: str, retries: int = 2) -> list[dict[str, Any]]:
        """Run a SPARQL SELECT and return the raw ``bindings`` list.

        Retries on 5xx errors with a short backoff, since the Wikidata
        Query Service returns 502/503 under load.
        """
        import time

        for attempt in range(retries + 1):
            resp = self._http.get(SPARQL_ENDPOINT, params={"query": query, "format": "json"})
            if resp.status_code >= 500 and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", {}).get("bindings", [])
        return []

    # ------------------------------------------------------------------
    # Generic statement fetch -- used by the new graph-model sync.
    # ------------------------------------------------------------------

    def fetch_statements(self, qids: list[str], pids: list[str]) -> list[dict[str, Any]]:
        """Return ``(item_qid, pid, value, value_label, rank)`` tuples as dicts.

        Batched across ``qids`` in groups of :data:`BATCH_SIZE`. ``pids``
        should be Wikidata property ids (``P27``, ``P569``, ...); results
        cover whichever of them are declared on each item.

        ``value`` is either the referenced item's QID (for entity-typed
        properties) or a literal; ``value_label`` is the English label
        wikibase:labels returned for the value.
        """
        if not qids or not pids:
            return []
        pid_values = " ".join(f"wd:{p}" for p in pids)
        results: list[dict[str, Any]] = []
        for i in range(0, len(qids), BATCH_SIZE):
            batch = qids[i : i + BATCH_SIZE]
            item_values = " ".join(f"wd:{q}" for q in batch)
            query = f"""
            SELECT ?item ?p ?v ?vLabel ?rank WHERE {{
              VALUES ?item {{ {item_values} }}
              VALUES ?p {{ {pid_values} }}
              ?item ?claim ?statement.
              ?statement ?ps ?v;
                         wikibase:rank ?rank.
              FILTER(?rank != wikibase:DeprecatedRank)
              ?p wikibase:claim ?claim;
                 wikibase:statementProperty ?ps.
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
            }}
            """
            for b in self.sparql(query):
                qid = _qid_from_uri(_val(b.get("item")))
                pid = _qid_from_uri(_val(b.get("p")))
                raw_value = _val(b.get("v"))
                if not qid or not pid or raw_value is None:
                    continue
                value = _qid_from_uri(raw_value) or raw_value
                value_is_entity = bool(_qid_from_uri(raw_value))
                results.append(
                    {
                        "qid": qid,
                        "pid": pid,
                        "value": value,
                        "value_label": _val(b.get("vLabel")) or value,
                        "rank": _rank_suffix(_val(b.get("rank"))),
                        "value_type": "entity" if value_is_entity else "string",
                    }
                )
        return results

    def fetch_instances_with_properties(
        self, class_qid: str, pids: list[str], limit: int = SEED_LIMIT
    ) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
        """Fetch instances of a class AND their properties in two passes.

        Returns ``(instances, statements)`` where:
        - ``instances`` is ``[{"qid": "Q183", "label": "Germany"}, ...]``
        - ``statements`` is the same shape as :meth:`fetch_statements` output

        First fetches instance QIDs+labels, then batch-fetches their
        properties via :meth:`fetch_statements`.
        """
        instances = self.fetch_instances(class_qid, limit=limit)
        if not instances or not pids:
            return instances, []
        qids = [instance["qid"] for instance in instances]
        statements = self.fetch_statements(qids, pids)
        return instances, statements

    def fetch_instances(self, class_qid: str, limit: int = SEED_LIMIT) -> list[dict[str, str]]:
        """Fetch the top ``limit`` instances of a Wikidata class.

        Returns ``[{"qid": "Q183", "label": "Germany"}, ...]`` ordered by
        number of Wikipedia sitelinks (a proxy for notability).

        The query uses a high sitelinks threshold (50) to pre-filter and
        avoids the label SERVICE (which can timeout on large result sets),
        fetching labels in a separate batched pass instead.
        """
        # Step 1: fetch QIDs only (fast, no label resolution).
        query = f"""
        SELECT ?item ?sl WHERE {{
          ?item wdt:P31 wd:{class_qid};
                wikibase:sitelinks ?sl.
          FILTER(?sl >= 50)
        }}
        ORDER BY DESC(?sl)
        LIMIT {limit}
        """
        qids: list[str] = []
        for binding in self.sparql(query):
            qid = _qid_from_uri(_val(binding.get("item")))
            if qid:
                qids.append(qid)
        if not qids:
            return []

        # Step 2: fetch labels in batches (label SERVICE is fast with VALUES).
        results: list[dict[str, str]] = []
        for batch_start in range(0, len(qids), BATCH_SIZE):
            batch = qids[batch_start : batch_start + BATCH_SIZE]
            values = " ".join(f"wd:{q}" for q in batch)
            label_query = f"""
            SELECT ?item ?itemLabel WHERE {{
              VALUES ?item {{ {values} }}
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
            }}
            """
            labels: dict[str, str] = {}
            for binding in self.sparql(label_query):
                qid = _qid_from_uri(_val(binding.get("item")))
                label = _val(binding.get("itemLabel")) or ""
                if qid and label:
                    labels[qid] = label
            for qid in batch:
                label = labels.get(qid, qid)
                results.append({"qid": qid, "label": label})
        return results


def _val(binding: dict[str, Any] | None) -> str | None:
    if not binding:
        return None
    v = binding.get("value")
    return v if isinstance(v, str) and v else None


def _qid_from_uri(uri: str | None) -> str | None:
    """http://www.wikidata.org/entity/Q183 -> Q183 (same for P-ids)."""
    if not uri:
        return None
    tail = uri.rsplit("/", 1)[-1]
    return tail if tail.startswith(("Q", "P")) else None


def _rank_suffix(uri: str | None) -> str:
    """Wikidata rank is a URI like http://wikiba.se/ontology#NormalRank -> normal."""
    if not uri:
        return "normal"
    tail = uri.rsplit("#", 1)[-1].replace("Rank", "").lower()
    return tail or "normal"
