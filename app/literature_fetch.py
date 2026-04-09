"""Fetch and extract research findings from free academic APIs.

Two data sources:

1. **OpenAlex** (primary) -- free, no API key required. Structured
   concept taxonomy, citation counts, abstracts. Covers PubMed +
   social science + psychology.

2. **Semantic Scholar** (secondary) -- free tier, TLDR summaries,
   citation graph traversal.

The extraction pipeline:

1. For each pair of Field categories present in the user's installed
   datasets, construct a search query and fetch top-cited papers.
2. Send each paper's abstract to the LLM to extract a structured
   Finding (exposure, outcome, direction, effect size, temporal lag).
3. Store in ``shenas_system.literature_findings`` (dedup by openalex_id).

Privacy: only published paper abstracts go to the LLM. No personal data.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import httpx
from pydantic import BaseModel

log = logging.getLogger(__name__)


class OpenAlexPaper(BaseModel):
    openalex_id: str = ""
    title: str = ""
    abstract: str = ""
    doi: str = ""
    citation_count: int = 0
    publication_year: int | None = None
    type: str = ""


class SemanticScholarPaper(BaseModel):
    paper_id: str = ""
    title: str = ""
    abstract: str = ""
    tldr: str = ""
    doi: str = ""
    citation_count: int = 0
    year: int | None = None


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
# OpenAlex client
# ------------------------------------------------------------------

OPENALEX_BASE = "https://api.openalex.org"
OPENALEX_MAILTO = "shenas@example.com"  # polite pool identifier


def search_openalex(
    query: str,
    *,
    min_citations: int = 50,
    per_page: int = 10,
    filter_type: str | None = "review",
) -> list[OpenAlexPaper]:
    """Search OpenAlex for papers matching a query."""
    params: dict[str, Any] = {
        "search": query,
        "per_page": per_page,
        "sort": "cited_by_count:desc",
        "mailto": OPENALEX_MAILTO,
    }
    filters = [f"cited_by_count:>{min_citations}"]
    if filter_type:
        filters.append(f"type:{filter_type}")
    params["filter"] = ",".join(filters)

    try:
        resp = httpx.get(f"{OPENALEX_BASE}/works", params=params, timeout=15)
        resp.raise_for_status()
    except httpx.HTTPError:
        log.warning("OpenAlex search failed for query: %s", query, exc_info=True)
        return []

    results: list[OpenAlexPaper] = []
    for work in resp.json().get("results", []):
        abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
        if not abstract:
            continue
        results.append(
            OpenAlexPaper(
                openalex_id=work.get("id", ""),
                title=work.get("title", ""),
                abstract=abstract,
                doi=work.get("doi", ""),
                citation_count=work.get("cited_by_count", 0),
                publication_year=work.get("publication_year"),
                type=work.get("type", ""),
            )
        )
    return results


def _reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct abstract text from OpenAlex's inverted index format."""
    if not inverted_index:
        return ""
    word_positions: list[tuple[int, str]] = [(pos, word) for word, positions in inverted_index.items() for pos in positions]
    word_positions.sort()
    return " ".join(word for _, word in word_positions)


# ------------------------------------------------------------------
# Semantic Scholar client
# ------------------------------------------------------------------

SEMSCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"


def search_semantic_scholar(
    query: str,
    *,
    limit: int = 10,
    min_citations: int = 50,
) -> list[SemanticScholarPaper]:
    """Search Semantic Scholar for papers matching a query."""
    params: dict[str, str | int] = {
        "query": query,
        "limit": limit,
        "fields": "title,abstract,tldr,externalIds,citationCount,year",
        "minCitationCount": min_citations,
    }

    try:
        resp = httpx.get(f"{SEMSCHOLAR_BASE}/paper/search", params=params, timeout=15)
        resp.raise_for_status()
    except httpx.HTTPError:
        log.warning("Semantic Scholar search failed for query: %s", query, exc_info=True)
        return []

    results: list[SemanticScholarPaper] = []
    for paper in resp.json().get("data", []):
        abstract = paper.get("abstract") or ""
        tldr = paper.get("tldr", {})
        tldr_text = tldr.get("text", "") if isinstance(tldr, dict) else ""
        text = abstract or tldr_text
        if not text:
            continue
        external = paper.get("externalIds") or {}
        results.append(
            SemanticScholarPaper(
                paper_id=paper.get("paperId", ""),
                title=paper.get("title", ""),
                abstract=text,
                tldr=tldr_text,
                doi=external.get("DOI", ""),
                citation_count=paper.get("citationCount", 0),
                year=paper.get("year"),
            )
        )
    return results


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
# Refresh: end-to-end pipeline
# ------------------------------------------------------------------


def refresh_findings(
    catalog: dict[str, dict[str, Any]],
    provider: Any,
    *,
    papers_per_pair: int = 5,
    min_citations: int = 50,
) -> dict[str, Any]:
    """Fetch papers for all category pairs and extract findings.

    Returns a summary dict with counts of papers fetched, findings
    extracted, and findings skipped.
    """
    from app.literature import Finding, extract_catalog_categories

    categories = extract_catalog_categories(catalog)
    pairs = category_search_pairs(categories)

    stats = {"pairs": len(pairs), "papers_fetched": 0, "findings_extracted": 0, "skipped": 0, "duplicates": 0}

    for cat_a, cat_b in pairs:
        query = build_search_query(cat_a, cat_b)
        papers = search_openalex(query, per_page=papers_per_pair, min_citations=min_citations)
        stats["papers_fetched"] += len(papers)

        for paper in papers:
            oa_id = paper.openalex_id
            if oa_id and Finding.by_openalex_id(oa_id) is not None:
                stats["duplicates"] += 1
                continue

            citation = f"{paper.title}, {paper.publication_year}" if paper.publication_year else paper.title
            result = extract_finding_from_abstract(
                provider,
                title=paper.title,
                abstract=paper.abstract,
                citation=citation,
            )

            if result is None:
                stats["skipped"] += 1
                continue

            finding = Finding(
                exposure=result.exposure,
                outcome=result.outcome,
                direction=result.direction,
                effect_size=result.effect_size,
                effect_size_type=result.effect_size_type,
                lag_hours=result.lag_hours,
                lag_max_hours=result.lag_max_hours,
                evidence_level=result.evidence_level,
                sample_size=result.sample_size,
                population=result.population,
                mechanism=result.mechanism,
                citation=citation,
                doi=paper.doi or "",
                source_api="openalex",
                exposure_categories=result.exposure_categories or f"{cat_a}",
                outcome_categories=result.outcome_categories or f"{cat_b}",
                openalex_id=oa_id,
            )
            finding.insert()
            stats["findings_extracted"] += 1

    return stats
