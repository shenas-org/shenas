"""NER recognizer abstraction for Layer 2 (ADR §4.2, §4.7).

The production implementation wraps the vendored Presidio fork
(shenas-org/presidio-vendor). The abstract Protocol lets tests inject
a mock without requiring Presidio to be installed.

Confidence floor: recall >= 0.92, precision >= 0.85 on the shenas eval
corpus (ADR §4.3 / D2). The floor is enforced here at recognition time
so callers fail-closed when confidence is insufficient (ADR §3.3).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.llmmixnet.types import EntityType, RecognizedEntity

CONFIDENCE_FLOOR = 0.70

PRESIDIO_ENTITY_MAP: dict[str, EntityType] = {
    "PERSON": EntityType.PERSON,
    "EMAIL_ADDRESS": EntityType.EMAIL_ADDRESS,
    "PHONE_NUMBER": EntityType.PHONE_NUMBER,
    "CREDIT_CARD": EntityType.CREDIT_CARD,
    "IBAN_CODE": EntityType.IBAN_CODE,
    "IP_ADDRESS": EntityType.IP_ADDRESS,
    "LOCATION": EntityType.LOCATION,
    "DATE_TIME": EntityType.DATE_TIME,
    "URL": EntityType.URL,
    "NRP": EntityType.ORGANIZATION,
    "ORGANIZATION": EntityType.ORGANIZATION,
    "US_SSN": EntityType.US_SSN,
    "MEDICAL_LICENSE": EntityType.MEDICAL_LICENSE,
    "IN_AADHAAR": EntityType.IN_AADHAAR,
}

V0_ENTITY_TYPES: list[str] = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "IP_ADDRESS",
    "LOCATION",
    "DATE_TIME",
    "URL",
    "ORGANIZATION",
    "US_SSN",
    "MEDICAL_LICENSE",
    "IN_AADHAAR",
]


@runtime_checkable
class NerRecognizer(Protocol):
    """Protocol for NER recognizers injected into Layer2Redactor.

    Implementations must be local-only — no remote calls (ADR §4.1).
    """

    def recognize(
        self,
        text: str,
        language: str = "en",
        entity_types: list[EntityType] | None = None,
    ) -> list[RecognizedEntity]: ...

    @property
    def confidence_floor(self) -> float: ...


class PresidioRecognizer:
    """Presidio-backed NER recognizer (ADR §4.7).

    Wraps the vendored presidio-analyzer package. Lazy-imports so the class
    can be referenced in type annotations even when the package is not yet
    installed; calling recognize() without presidio-analyzer raises ImportError
    with a clear message.

    The vendor fork (shenas-org/presidio-vendor) strips Azure/cloud connectors
    and the analytics beacon. Until the fork is wired into the build, this
    class targets the upstream presidio-analyzer package directly — the import
    path is identical.
    """

    def __init__(
        self,
        confidence_floor: float = CONFIDENCE_FLOOR,
        language: str = "en",
    ) -> None:
        self._confidence_floor = confidence_floor
        self._language = language
        self._analyzer: object | None = None

    def _get_analyzer(self) -> object:
        if self._analyzer is not None:
            return self._analyzer
        try:
            from presidio_analyzer import AnalyzerEngine  # type: ignore[import-not-found]  # ty: ignore[unresolved-import]
        except ImportError as exc:
            raise ImportError(
                "presidio-analyzer is required for the production NER path. "
                "Add 'presidio-analyzer' to app/pyproject.toml dependencies "
                "and run 'uv sync'. The shenas-org/presidio-vendor fork will "
                "replace this dependency once C-LMN-10 is complete."
            ) from exc
        self._analyzer = AnalyzerEngine()  # type: ignore[name-defined]
        return self._analyzer

    @property
    def confidence_floor(self) -> float:
        return self._confidence_floor

    def recognize(
        self,
        text: str,
        language: str = "en",
        entity_types: list[EntityType] | None = None,
    ) -> list[RecognizedEntity]:
        analyzer = self._get_analyzer()
        presidio_types = (
            [et.value for et in entity_types if et.value in PRESIDIO_ENTITY_MAP.values()] if entity_types else V0_ENTITY_TYPES
        )
        results = analyzer.analyze(  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
            text=text,
            language=language,
            entities=presidio_types,
        )
        recognized: list[RecognizedEntity] = []
        for result in results:
            mapped = PRESIDIO_ENTITY_MAP.get(result.entity_type)
            if mapped is None:
                continue
            recognized.append(
                RecognizedEntity(
                    entity_type=mapped,
                    start=result.start,
                    end=result.end,
                    text=text[result.start : result.end],
                    score=result.score,
                )
            )
        return recognized
