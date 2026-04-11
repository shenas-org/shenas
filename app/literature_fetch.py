"""Fetch and extract research findings via the shenas.net API gateway.

The local app never calls academic paper APIs directly. Instead it
sends category pairs to the ``/api/literature/refresh`` endpoint on
shenas.net, which searches multiple academic databases, extracts
structured findings via the LLM, and returns them as JSON. The local
app stores the findings in its encrypted DuckDB.

For users with a local Anthropic API key (no shenas.net account), the
LLM extraction can also run locally against papers returned by the
gateway's ``/api/literature/papers`` endpoint.

Privacy: only published paper abstracts go to the LLM. No personal data.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Literal

from pydantic import BaseModel

log = logging.getLogger(__name__)

SHENAS_NET_URL = os.environ.get("SHENAS_NET_URL", "https://shenas.net")


class Paper(BaseModel):
    """Unified academic paper returned by the API gateway.

    Merges results from multiple academic databases into a single model.
    The ``source_ref`` is an opaque identifier used for deduplication.
    """

    source_ref: str = ""
    title: str = ""
    abstract: str = ""
    doi: str = ""
    citation_count: int = 0
    publication_year: int | None = None


class ExtractedFinding(BaseModel):
    """Structured finding extracted by the LLM from a paper abstract."""

    exposure: str
    outcome: str
    direction: Literal["positive", "negative", "u_shaped", "null"]
    effect_size: float | None = None
    effect_size_type: Literal["r", "d", "odds_ratio", "risk_ratio"] | None = None
    lag_hours: float | None = None
    lag_max_hours: float | None = None
    evidence_level: Literal["meta_analysis", "rct", "longitudinal", "cross_sectional", "case_report"]
    sample_size: int | None = None
    population: Literal["healthy_adults", "athletes", "clinical", "elderly", "mixed"] | None = None
    mechanism: str | None = None
    exposure_categories: str = ""
    outcome_categories: str = ""
    skip: bool = False


class HypothesisSuggestion(BaseModel):
    """A hypothesis suggestion derived from a literature finding."""

    question: str
    finding_id: int
    exposure: str
    outcome: str
    direction: str
    effect_size: float | None = None
    evidence_level: str = ""
    citation: str = ""
    evidence_rank: int = 0


# Map Field.category values to search-friendly terms for academic APIs.
CATEGORY_SEARCH_TERMS: dict[str, list[str]] = {
    "cardiovascular": ["heart rate variability", "resting heart rate", "HRV", "cardiovascular"],
    "sleep": ["sleep quality", "sleep duration", "sleep architecture", "insomnia"],
    "activity": ["physical exercise", "physical activity", "aerobic exercise", "steps"],
    "body_composition": ["body weight", "BMI", "body fat", "body composition"],
    "wellbeing": ["mood", "subjective wellbeing", "life satisfaction", "affect"],
    "performance": ["cognitive performance", "productivity", "attention", "executive function"],
    "social": ["social interaction", "loneliness", "social support", "social connection"],
    "growth": ["learning", "skill acquisition", "language learning", "education"],
    "spending": ["financial stress", "spending behavior", "financial wellbeing", "debt"],
    "income": ["income", "financial security", "socioeconomic status"],
    "health": ["health behavior", "chronic pain", "inflammation", "skin condition"],
    "time": [],  # skip -- too generic
}


# ------------------------------------------------------------------
# LLM-based finding extraction
# ------------------------------------------------------------------


def extract_finding_tool() -> dict[str, Any]:
    """Anthropic tool definition for structured finding extraction."""
    return {
        "name": "extract_finding",
        "description": (
            "Extract a structured research finding from a paper's title and abstract. "
            "Identify the primary exposure (cause) and outcome (effect) variables, "
            "the direction and magnitude of the effect, any temporal lag, and the "
            "study design / evidence level."
        ),
        "input_schema": ExtractedFinding.model_json_schema(),
    }


def extract_finding_from_abstract(
    provider: Any,
    title: str,
    abstract: str,
    *,
    citation: str = "",
) -> ExtractedFinding | None:
    """Use the LLM to extract a structured finding from a paper abstract.

    Returns an ExtractedFinding, or None if the paper should be skipped.
    """
    system = (
        "You are a research literature analyst. Extract structured findings "
        "from paper abstracts for a personal data analytics system. Focus on "
        "findings relevant to personal health, behavior, productivity, finance, "
        "and wellbeing. Use the extract_finding tool to submit your extraction."
    )
    user = f"## Paper\n\nTitle: {title}\n\nAbstract: {abstract}\n\nCitation: {citation}"
    tools = [extract_finding_tool()]

    try:
        payload = provider.ask(system=system, user=user, tools=tools)
    except Exception:
        log.warning("LLM extraction failed for: %s", title, exc_info=True)
        return None

    try:
        finding = ExtractedFinding.model_validate(payload)
    except Exception:
        log.warning("LLM returned invalid finding for: %s", title, exc_info=True)
        return None

    if finding.skip:
        return None

    return finding


# ------------------------------------------------------------------
# Category pair generation
# ------------------------------------------------------------------


def category_search_pairs(categories: set[str]) -> list[tuple[str, str]]:
    """Generate (exposure_query, outcome_query) search pairs from installed categories.

    Only generates pairs where both categories have search terms and
    are distinct. Avoids duplicate (A,B)/(B,A) pairs.
    """
    cats = sorted(categories & set(CATEGORY_SEARCH_TERMS))
    pairs: list[tuple[str, str]] = []
    for i, a in enumerate(cats):
        for b in cats[i + 1 :]:
            terms_a = CATEGORY_SEARCH_TERMS.get(a, [])
            terms_b = CATEGORY_SEARCH_TERMS.get(b, [])
            if terms_a and terms_b:
                pairs.append((a, b))
    return pairs


def build_search_query(cat_a: str, cat_b: str) -> str:
    """Build a search query string from two category names."""
    terms_a = CATEGORY_SEARCH_TERMS.get(cat_a, [cat_a])
    terms_b = CATEGORY_SEARCH_TERMS.get(cat_b, [cat_b])
    # Use the first (most representative) term from each category.
    return f"{terms_a[0]} {terms_b[0]}"


# ------------------------------------------------------------------
# Gateway client
# ------------------------------------------------------------------


def _get_remote_token() -> str | None:
    """Return the current user's remote_token, or None."""
    try:
        from app.db import current_user_id, cursor

        uid = current_user_id.get()
        if not uid:
            return None
        with cursor(database="shenas") as cur:
            row = cur.execute(
                "SELECT remote_token FROM shenas_system.local_users WHERE id = ?",
                [uid],
            ).fetchone()
            return row[0] if row and row[0] else None
    except Exception:
        return None


def refresh_findings(
    catalog: dict[str, dict[str, Any]],
    *,
    papers_per_pair: int = 5,
    min_citations: int = 50,
) -> dict[str, Any]:
    """Refresh literature findings via the shenas.net API gateway.

    Sends installed data categories + known source refs to the gateway,
    which searches academic databases, extracts findings via LLM, and
    returns them. Findings are stored in the local encrypted DB.

    Returns a summary dict with counts.
    """
    from app.literature import Finding, extract_catalog_categories

    categories = list(extract_catalog_categories(catalog))
    if not categories:
        return {"pairs": 0, "papers_fetched": 0, "findings_extracted": 0, "skipped": 0, "duplicates": 0}

    token = _get_remote_token()
    if not token:
        msg = "Literature refresh requires a shenas.net account. Sign in via Settings to use this feature."
        raise RuntimeError(msg)

    known_refs = [f.source_ref for f in Finding.all() if f.source_ref]

    payload = json.dumps(
        {
            "categories": categories,
            "papers_per_pair": papers_per_pair,
            "min_citations": min_citations,
            "known_source_refs": known_refs,
        }
    ).encode()

    req = urllib.request.Request(
        f"{SHENAS_NET_URL}/api/literature/refresh",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode() if exc.fp else ""
        msg = f"Literature refresh failed: {exc.code} -- {body}"
        raise RuntimeError(msg) from exc

    # Store findings locally
    for f in data.get("findings", []):
        Finding(
            exposure=f.get("exposure", ""),
            outcome=f.get("outcome", ""),
            direction=f.get("direction", ""),
            effect_size=f.get("effect_size"),
            effect_size_type=f.get("effect_size_type"),
            lag_hours=f.get("lag_hours"),
            lag_max_hours=f.get("lag_max_hours"),
            evidence_level=f.get("evidence_level", "cross_sectional"),
            sample_size=f.get("sample_size"),
            population=f.get("population"),
            mechanism=f.get("mechanism"),
            citation=f.get("citation", ""),
            doi=f.get("doi", ""),
            source_kind=f.get("source_kind", ""),
            exposure_categories=f.get("exposure_categories", ""),
            outcome_categories=f.get("outcome_categories", ""),
            source_ref=f.get("source_ref", ""),
        ).insert()

    return data.get("stats", {})
