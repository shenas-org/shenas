"""Server-side literature refresh endpoint.

Runs the full pipeline server-side: fetches papers from OpenAlex and
Semantic Scholar, extracts structured findings via the LLM, and returns
them as JSON. The local app stores the findings in its encrypted DB.

This avoids the local app needing an Anthropic API key or making
outbound calls to academic APIs.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from shenas_net_api.auth import get_current_user

router = APIRouter(prefix="/literature")

log = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ------------------------------------------------------------------
# OpenAlex
# ------------------------------------------------------------------

OPENALEX_BASE = "https://api.openalex.org"
OPENALEX_MAILTO = "shenas@shenas.net"


def _search_openalex(query: str, *, per_page: int = 5, min_citations: int = 50) -> list[dict[str, Any]]:
    """Search OpenAlex and return unified paper dicts."""
    params: dict[str, Any] = {
        "search": query,
        "per_page": per_page,
        "sort": "cited_by_count:desc",
        "mailto": OPENALEX_MAILTO,
        "filter": f"cited_by_count:>{min_citations},type:review",
    }
    try:
        resp = httpx.get(f"{OPENALEX_BASE}/works", params=params, timeout=15)
        resp.raise_for_status()
    except Exception:
        log.warning("OpenAlex search failed for: %s", query, exc_info=True)
        return []

    results = []
    for work in resp.json().get("results", []):
        abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
        if not abstract:
            continue
        results.append(
            {
                "source_ref": work.get("id", ""),
                "source_kind": "openalex",
                "title": work.get("title", ""),
                "abstract": abstract,
                "doi": work.get("doi", ""),
                "citation_count": work.get("cited_by_count", 0),
                "publication_year": work.get("publication_year"),
            }
        )
    return results


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    word_positions = [(pos, word) for word, positions in inverted_index.items() for pos in positions]
    word_positions.sort()
    return " ".join(word for _, word in word_positions)


# ------------------------------------------------------------------
# Semantic Scholar
# ------------------------------------------------------------------

SEMSCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"


def _search_semantic_scholar(query: str, *, limit: int = 5, min_citations: int = 50) -> list[dict[str, Any]]:
    """Search Semantic Scholar and return unified paper dicts."""
    params: dict[str, str | int] = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,tldr,externalIds,citationCount,year",
        "minCitationCount": min_citations,
    }
    try:
        resp = httpx.get(f"{SEMSCHOLAR_BASE}/paper/search", params=params, timeout=15)
        resp.raise_for_status()
    except Exception:
        log.warning("Semantic Scholar search failed for: %s", query, exc_info=True)
        return []

    results = []
    for paper in resp.json().get("data", []):
        abstract = paper.get("abstract") or ""
        tldr = paper.get("tldr", {})
        tldr_text = tldr.get("text", "") if isinstance(tldr, dict) else ""
        text = abstract or tldr_text
        if not text:
            continue
        external = paper.get("externalIds") or {}
        results.append(
            {
                "source_ref": f"s2:{paper.get('paperId', '')}",
                "source_kind": "semantic_scholar",
                "title": paper.get("title", ""),
                "abstract": text,
                "doi": external.get("DOI", ""),
                "citation_count": paper.get("citationCount", 0),
                "publication_year": paper.get("year"),
            }
        )
    return results


# ------------------------------------------------------------------
# Unified paper search
# ------------------------------------------------------------------


def _search_papers(query: str, *, per_page: int = 5, min_citations: int = 50) -> list[dict[str, Any]]:
    """Search both academic databases and merge results, deduped by DOI."""
    oa_papers = _search_openalex(query, per_page=per_page, min_citations=min_citations)
    ss_papers = _search_semantic_scholar(query, limit=per_page, min_citations=min_citations)

    seen_dois: set[str] = set()
    merged: list[dict[str, Any]] = []

    for paper in oa_papers:
        doi = paper.get("doi", "")
        if doi:
            seen_dois.add(doi)
        merged.append(paper)

    for paper in ss_papers:
        doi = paper.get("doi", "")
        if doi and doi in seen_dois:
            continue
        if doi:
            seen_dois.add(doi)
        merged.append(paper)

    return merged


# ------------------------------------------------------------------
# LLM extraction
# ------------------------------------------------------------------

EXTRACT_PROMPT = (
    "You are a research literature analyst. Extract structured findings "
    "from paper abstracts for a personal data analytics system. Focus on "
    "findings relevant to personal health, behavior, productivity, finance, "
    "and wellbeing. Respond with a JSON object containing: exposure, outcome, "
    "direction (positive/negative/u_shaped/null), effect_size, effect_size_type, "
    "lag_hours, lag_max_hours, evidence_level (meta_analysis/rct/longitudinal/"
    "cross_sectional/case_report), sample_size, population, mechanism, "
    "exposure_categories, outcome_categories, skip (boolean)."
)


def _extract_finding(title: str, abstract: str, citation: str) -> dict[str, Any] | None:
    """Call Anthropic to extract a structured finding from a paper abstract."""
    payload = json.dumps(
        {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 500,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"{EXTRACT_PROMPT}\n\n## Paper\n\nTitle: {title}\n\nAbstract: {abstract}\n\nCitation: {citation}"
                    ),
                }
            ],
        }
    ).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            text = data["content"][0]["text"]
            finding = json.loads(text)
            if finding.get("skip"):
                return None
            return finding
    except Exception:
        log.warning("LLM extraction failed for: %s", title, exc_info=True)
        return None


# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------

# Reuse the same category search terms as the local module.
CATEGORY_SEARCH_TERMS: dict[str, list[str]] = {
    "cardiovascular": ["heart rate variability", "resting heart rate", "HRV"],
    "sleep": ["sleep quality", "sleep duration", "sleep architecture"],
    "activity": ["physical exercise", "physical activity", "aerobic exercise"],
    "body_composition": ["body weight", "BMI", "body fat"],
    "wellbeing": ["mood", "subjective wellbeing", "life satisfaction"],
    "performance": ["cognitive performance", "productivity", "attention"],
    "social": ["social interaction", "loneliness", "social support"],
    "growth": ["learning", "skill acquisition", "language learning"],
    "spending": ["financial stress", "spending behavior", "financial wellbeing"],
    "income": ["income", "financial security", "socioeconomic status"],
    "health": ["health behavior", "chronic pain", "inflammation"],
}


class RefreshRequest(BaseModel):
    categories: list[str] = Field(description="Field categories from the user's installed datasets")
    papers_per_pair: int = 5
    min_citations: int = 50
    known_source_refs: list[str] = Field(default_factory=list, description="Source refs already in the local DB for dedup")


class ExtractedFinding(BaseModel):
    exposure: str = ""
    outcome: str = ""
    direction: str = ""
    effect_size: float | None = None
    effect_size_type: str | None = None
    lag_hours: float | None = None
    lag_max_hours: float | None = None
    evidence_level: str = "cross_sectional"
    sample_size: int | None = None
    population: str | None = None
    mechanism: str | None = None
    citation: str = ""
    doi: str = ""
    source_kind: str = ""
    exposure_categories: str = ""
    outcome_categories: str = ""
    source_ref: str = ""


# ------------------------------------------------------------------
# Endpoint
# ------------------------------------------------------------------


@router.post("/refresh")
async def refresh(request: Request, body: RefreshRequest) -> dict:
    """Run the full literature refresh pipeline server-side."""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="LLM service not configured")

    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    known_refs = set(body.known_source_refs)
    categories = set(body.categories) & set(CATEGORY_SEARCH_TERMS)

    # Generate category pairs
    cats = sorted(categories)
    pairs = [
        (a, b)
        for i, a in enumerate(cats)
        for b in cats[i + 1 :]
        if CATEGORY_SEARCH_TERMS.get(a) and CATEGORY_SEARCH_TERMS.get(b)
    ]

    stats = {"pairs": len(pairs), "papers_fetched": 0, "findings_extracted": 0, "skipped": 0, "duplicates": 0}
    findings: list[dict[str, Any]] = []

    for cat_a, cat_b in pairs:
        terms_a = CATEGORY_SEARCH_TERMS[cat_a]
        terms_b = CATEGORY_SEARCH_TERMS[cat_b]
        query = f"{terms_a[0]} {terms_b[0]}"

        papers = _search_papers(query, per_page=body.papers_per_pair, min_citations=body.min_citations)
        stats["papers_fetched"] += len(papers)

        for paper in papers:
            ref = paper["source_ref"]
            if ref in known_refs:
                stats["duplicates"] += 1
                continue

            year = paper.get("publication_year", "")
            citation = f"{paper['title']}, {year}" if year else paper["title"]

            result = _extract_finding(paper["title"], paper["abstract"], citation)
            if result is None:
                stats["skipped"] += 1
                continue

            findings.append(
                {
                    **result,
                    "citation": citation,
                    "doi": paper.get("doi", ""),
                    "source_kind": paper.get("source_kind", ""),
                    "exposure_categories": result.get("exposure_categories", cat_a),
                    "outcome_categories": result.get("outcome_categories", cat_b),
                    "source_ref": ref,
                }
            )
            stats["findings_extracted"] += 1
            known_refs.add(ref)

    return {"stats": stats, "findings": findings}
