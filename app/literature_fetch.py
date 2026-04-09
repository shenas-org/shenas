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
from typing import Any

import httpx

log = logging.getLogger(__name__)

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
) -> list[dict[str, Any]]:
    """Search OpenAlex for papers matching a query.

    Returns a list of work dicts with keys: openalex_id, title,
    abstract, doi, citation_count, publication_year, type.

    Filters to highly-cited papers and optionally to reviews/meta-analyses.
    """
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

    results: list[dict[str, Any]] = []
    for work in resp.json().get("results", []):
        abstract = _reconstruct_abstract(work.get("abstract_inverted_index"))
        if not abstract:
            continue
        results.append(
            {
                "openalex_id": work.get("id", ""),
                "title": work.get("title", ""),
                "abstract": abstract,
                "doi": work.get("doi", ""),
                "citation_count": work.get("cited_by_count", 0),
                "publication_year": work.get("publication_year"),
                "type": work.get("type", ""),
            }
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
) -> list[dict[str, Any]]:
    """Search Semantic Scholar for papers matching a query.

    Returns a list of paper dicts with keys: paper_id, title, abstract,
    tldr, doi, citation_count, year.
    """
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

    results: list[dict[str, Any]] = []
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
                "paper_id": paper.get("paperId", ""),
                "title": paper.get("title", ""),
                "abstract": text,
                "tldr": tldr_text,
                "doi": external.get("DOI", ""),
                "citation_count": paper.get("citationCount", 0),
                "year": paper.get("year"),
            }
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
        "input_schema": {
            "type": "object",
            "properties": {
                "exposure": {
                    "type": "string",
                    "description": "Causal/exposure variable in snake_case (e.g. alcohol_consumption, sleep_duration)",
                },
                "outcome": {
                    "type": "string",
                    "description": "Outcome/effect variable in snake_case (e.g. heart_rate_variability, mood)",
                },
                "direction": {
                    "type": "string",
                    "enum": ["positive", "negative", "u_shaped", "null"],
                    "description": "Direction of the effect",
                },
                "effect_size": {
                    "type": "number",
                    "description": "Standardized effect size (correlation r, Cohen's d, etc.). Null if not reported.",
                },
                "effect_size_type": {
                    "type": "string",
                    "enum": ["r", "d", "odds_ratio", "risk_ratio"],
                    "description": "Type of effect size reported",
                },
                "lag_hours": {
                    "type": "number",
                    "description": (
                        "Minimum temporal delay between exposure and outcome in hours. Null if not reported or concurrent."
                    ),
                },
                "lag_max_hours": {
                    "type": "number",
                    "description": "Maximum temporal delay in hours. Null if point estimate or not reported.",
                },
                "evidence_level": {
                    "type": "string",
                    "enum": ["meta_analysis", "rct", "longitudinal", "cross_sectional", "case_report"],
                    "description": "Study design / evidence level",
                },
                "sample_size": {
                    "type": "integer",
                    "description": "Total sample size (across studies for meta-analyses). Null if not reported.",
                },
                "population": {
                    "type": "string",
                    "enum": ["healthy_adults", "athletes", "clinical", "elderly", "mixed"],
                    "description": "Study population",
                },
                "mechanism": {
                    "type": "string",
                    "description": "One-sentence causal mechanism explanation",
                },
                "exposure_categories": {
                    "type": "string",
                    "description": (
                        "Comma-separated categories from: cardiovascular, sleep, activity,"
                        " body_composition, wellbeing, performance, social, growth, spending, income, health"
                    ),
                },
                "outcome_categories": {
                    "type": "string",
                    "description": "Comma-separated categories from the same list",
                },
                "skip": {
                    "type": "boolean",
                    "description": (
                        "Set to true if the paper doesn't contain a clear exposure->outcome"
                        " finding suitable for personal health/behavioral data analysis"
                    ),
                },
            },
            "required": [
                "exposure",
                "outcome",
                "direction",
                "evidence_level",
                "exposure_categories",
                "outcome_categories",
                "skip",
            ],
        },
    }


def extract_finding_from_abstract(
    provider: Any,
    title: str,
    abstract: str,
    *,
    citation: str = "",
) -> dict[str, Any] | None:
    """Use the LLM to extract a structured finding from a paper abstract.

    Returns a dict matching the Finding dataclass fields, or None if
    the paper should be skipped (not relevant / no clear finding).
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

    if payload.get("skip"):
        return None

    return {
        "exposure": payload.get("exposure", ""),
        "outcome": payload.get("outcome", ""),
        "direction": payload.get("direction", ""),
        "effect_size": payload.get("effect_size"),
        "effect_size_type": payload.get("effect_size_type"),
        "ci_low": None,
        "ci_high": None,
        "lag_hours": payload.get("lag_hours"),
        "lag_max_hours": payload.get("lag_max_hours"),
        "evidence_level": payload.get("evidence_level", "cross_sectional"),
        "sample_size": payload.get("sample_size"),
        "population": payload.get("population"),
        "mechanism": payload.get("mechanism"),
        "citation": citation,
        "exposure_categories": payload.get("exposure_categories", ""),
        "outcome_categories": payload.get("outcome_categories", ""),
    }


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
            # Dedup by OpenAlex ID.
            oa_id = paper.get("openalex_id", "")
            if oa_id and Finding.by_openalex_id(oa_id) is not None:
                stats["duplicates"] += 1
                continue

            year = paper.get("publication_year", "")
            citation = f"{paper['title']}, {year}" if year else paper["title"]
            result = extract_finding_from_abstract(
                provider,
                title=paper["title"],
                abstract=paper["abstract"],
                citation=citation,
            )

            if result is None:
                stats["skipped"] += 1
                continue

            finding = Finding(
                exposure=result["exposure"],
                outcome=result["outcome"],
                direction=result["direction"],
                effect_size=result.get("effect_size"),
                effect_size_type=result.get("effect_size_type"),
                ci_low=result.get("ci_low"),
                ci_high=result.get("ci_high"),
                lag_hours=result.get("lag_hours"),
                lag_max_hours=result.get("lag_max_hours"),
                evidence_level=result["evidence_level"],
                sample_size=result.get("sample_size"),
                population=result.get("population"),
                mechanism=result.get("mechanism"),
                citation=result.get("citation", ""),
                doi=paper.get("doi", ""),
                source_api="openalex",
                exposure_categories=result.get("exposure_categories", f"{cat_a}"),
                outcome_categories=result.get("outcome_categories", f"{cat_b}"),
                openalex_id=oa_id,
            )
            finding.insert()
            stats["findings_extracted"] += 1

    return stats
