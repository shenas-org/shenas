"""Research literature findings for hypothesis-informed RCA.

A :class:`Finding` is a structured representation of a published research
finding -- one directional relationship between an exposure variable and
an outcome variable, with effect size, temporal lag, evidence level, and
a citation. Stored in ``shenas_system.literature_findings``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from shenas_plugins.core.table import Field, Table

# Evidence level ordering for ranking (higher = stronger evidence).
EVIDENCE_RANK: dict[str, int] = {
    "meta_analysis": 4,
    "rct": 3,
    "longitudinal": 2,
    "cross_sectional": 1,
    "case_report": 0,
}


@dataclass
class Finding(Table):
    """One published research finding: exposure -> outcome with metadata."""

    class _Meta:
        name = "literature_findings"
        display_name = "Literature Findings"
        description = "Published research findings: exposure -> outcome with effect sizes and evidence levels."
        schema = "shenas_system"
        pk = ("id",)

    id: Annotated[
        int,
        Field(db_type="INTEGER", description="Finding ID", db_default="nextval('shenas_system.finding_seq')"),
    ] = 0
    exposure: Annotated[str, Field(db_type="VARCHAR", description="Causal variable (e.g. alcohol_consumption)")] = ""
    outcome: Annotated[str, Field(db_type="VARCHAR", description="Effect variable (e.g. heart_rate_variability)")] = ""
    direction: Annotated[
        str,
        Field(db_type="VARCHAR", description="Effect direction: positive, negative, u_shaped, null"),
    ] = ""
    effect_size: Annotated[float, Field(db_type="DOUBLE", description="Standardized effect size (r or d)")] | None = None
    effect_size_type: (
        Annotated[str, Field(db_type="VARCHAR", description="Effect size type: r, d, odds_ratio, risk_ratio")] | None
    ) = None
    ci_low: Annotated[float, Field(db_type="DOUBLE", description="95% CI lower bound")] | None = None
    ci_high: Annotated[float, Field(db_type="DOUBLE", description="95% CI upper bound")] | None = None
    lag_hours: (
        Annotated[float, Field(db_type="DOUBLE", description="Minimum temporal lag between cause and effect")] | None
    ) = None
    lag_max_hours: (
        Annotated[float, Field(db_type="DOUBLE", description="Maximum temporal lag between cause and effect")] | None
    ) = None
    evidence_level: Annotated[
        str,
        Field(
            db_type="VARCHAR", description="Evidence strength: meta_analysis, rct, longitudinal, cross_sectional, case_report"
        ),
    ] = ""
    sample_size: Annotated[int, Field(db_type="INTEGER", description="Total sample size")] | None = None
    population: (
        Annotated[str, Field(db_type="VARCHAR", description="Study population: healthy_adults, athletes, clinical")] | None
    ) = None
    mechanism: Annotated[str, Field(db_type="TEXT", description="Brief causal mechanism description")] | None = None
    citation: Annotated[str, Field(db_type="VARCHAR", description="Author et al., Year, Journal")] = ""
    doi: Annotated[str, Field(db_type="VARCHAR", description="DOI identifier")] | None = None
    source_kind: (
        Annotated[str, Field(db_type="VARCHAR", description="Origin API identifier", db_default="'curated'")] | None
    ) = None
    exposure_categories: Annotated[
        str,
        Field(db_type="VARCHAR", description="Comma-separated Field categories for the exposure variable"),
    ] = ""
    outcome_categories: Annotated[
        str,
        Field(db_type="VARCHAR", description="Comma-separated Field categories for the outcome variable"),
    ] = ""
    source_ref: Annotated[str, Field(db_type="VARCHAR", description="External paper ID for deduplication")] | None = None
    created_at: (
        Annotated[
            str,
            Field(db_type="TIMESTAMP", description="When this finding was extracted", db_default="current_timestamp"),
        ]
        | None
    ) = None

    # -- queries --

    @classmethod
    def for_categories(cls, *categories: str) -> list[Finding]:
        """Return findings where exposure or outcome touches any of the given categories."""
        if not categories:
            return []
        conditions = []
        params: list[str] = []
        for cat in categories:
            conditions.append("exposure_categories LIKE ?")
            conditions.append("outcome_categories LIKE ?")
            params.extend([f"%{cat}%", f"%{cat}%"])
        where = " OR ".join(conditions)
        return cls.all(where=where, params=params, order_by="evidence_level, id")

    @classmethod
    def for_question(cls, question: str, catalog: dict[str, dict[str, Any]]) -> list[Finding]:
        """Return findings relevant to a question, matched via the catalog's categories."""
        categories = cls.extract_catalog_categories(catalog)
        if not categories:
            return []
        findings = cls.for_categories(*categories)
        return cls._rank(findings, question)

    @classmethod
    def by_source_ref(cls, source_ref: str) -> Finding | None:
        """Look up a finding by its external paper ID (for dedup)."""
        rows = cls.all(where="source_ref = ?", params=[source_ref], limit=1)
        return rows[0] if rows else None

    # -- rendering --

    def to_prompt_line(self) -> str:
        """Render this finding as a compact one-liner for LLM prompts."""
        parts = [f"{self.exposure} -> {self.outcome} ({self.direction}"]
        if self.effect_size is not None:
            label = self.effect_size_type or "r"
            parts.append(f", {label}={self.effect_size}")
        if self.lag_hours is not None:
            if self.lag_max_hours is not None:
                parts.append(f", lag {self.lag_hours}-{self.lag_max_hours}h")
            else:
                parts.append(f", lag {self.lag_hours}h")
        parts.append(f", {self.evidence_level}")
        if self.sample_size is not None:
            parts.append(f", n={self.sample_size}")
        parts.append(")")
        line = "".join(parts)
        if self.mechanism:
            line += f"\n  Mechanism: {self.mechanism}"
        if self.citation:
            line += f"\n  Source: {self.citation}"
        return line

    def to_question(self) -> str:
        """Convert this finding into a natural-language hypothesis question."""
        exp = self.exposure.replace("_", " ")
        out = self.outcome.replace("_", " ")
        if self.direction == "positive":
            return f"Does higher {exp} predict higher {out}?"
        if self.direction == "negative":
            return f"Does higher {exp} predict lower {out}?"
        if self.direction == "u_shaped":
            return f"Is there a U-shaped relationship between {exp} and {out}?"
        return f"Is there a relationship between {exp} and {out}?"

    # -- catalog helpers --

    @staticmethod
    def extract_catalog_categories(catalog: dict[str, dict[str, Any]]) -> set[str]:
        """Extract all Field categories present in a catalog."""
        categories: set[str] = set()
        for table_meta in catalog.values():
            for col in table_meta.get("columns", []):
                cat = col.get("category")
                if cat:
                    categories.add(cat)
        return categories

    @classmethod
    def suggest_hypotheses(cls, catalog: dict[str, dict[str, Any]], *, limit: int = 10) -> list[Any]:
        """Generate hypothesis suggestions from findings cross-referenced with installed data."""
        from app.literature_fetch import HypothesisSuggestion

        categories = cls.extract_catalog_categories(catalog)
        if not categories:
            return []

        findings = cls.for_categories(*categories)
        suggestions: list[HypothesisSuggestion] = []

        for f in findings:
            exp_cats = set(f.exposure_categories.split(",")) if f.exposure_categories else set()
            out_cats = set(f.outcome_categories.split(",")) if f.outcome_categories else set()
            if not (exp_cats & categories) or not (out_cats & categories):
                continue
            suggestions.append(
                HypothesisSuggestion(
                    question=f.to_question(),
                    finding_id=f.id,
                    exposure=f.exposure,
                    outcome=f.outcome,
                    direction=f.direction,
                    effect_size=f.effect_size,
                    evidence_level=f.evidence_level,
                    citation=f.citation,
                    evidence_rank=EVIDENCE_RANK.get(f.evidence_level, 0),
                )
            )

        suggestions.sort(key=lambda s: (-s.evidence_rank, -(abs(s.effect_size or 0))))
        return suggestions[:limit]

    # -- ranking --

    @classmethod
    def _rank(cls, findings: list[Finding], question: str) -> list[Finding]:
        """Rank findings by relevance to a question."""
        q_words = set(question.lower().split())

        def _score(f: Finding) -> tuple[int, float, int]:
            ev = EVIDENCE_RANK.get(f.evidence_level, 0)
            es = abs(f.effect_size) if f.effect_size is not None else 0.0
            f_words = set(f.exposure.lower().replace("_", " ").split()) | set(f.outcome.lower().replace("_", " ").split())
            overlap = len(q_words & f_words)
            return (overlap, ev, -int(es * 1000))

        findings.sort(key=_score)
        return findings
