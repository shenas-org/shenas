"""Shared fixtures for LLMMixNet Layer 2 tests."""

from __future__ import annotations

import duckdb
import pytest

from app.llmmixnet.mapping import MappingStore
from app.llmmixnet.types import EntityType, RecognizedEntity


@pytest.fixture
def con() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB connection for tests."""
    return duckdb.connect(":memory:")


@pytest.fixture
def root_key_k1() -> bytes:
    return b"\x01" * 32


@pytest.fixture
def device_salt() -> bytes:
    return b"\x02" * 32


@pytest.fixture
def mapping_store(con, root_key_k1, device_salt) -> MappingStore:
    return MappingStore.from_root_key(con, root_key_k1, device_salt)


class StubNer:
    """Deterministic NER stub that detects bracketed test entities.

    Format: [TYPE:text] in the input maps to a RecognizedEntity with
    score 1.0. This lets tests exercise redaction logic without Presidio.

    Example: 'Hello [PERSON:Alice]!' → recognizes 'Alice' as PERSON at [7:12].
    """

    _PATTERN = __import__("re").compile(r"\[([A-Z_]+):([^\]]+)\]")
    _confidence_floor = 0.70

    @property
    def confidence_floor(self) -> float:
        return self._confidence_floor

    def recognize(
        self,
        text: str,
        language: str = "en",
        entity_types: list[EntityType] | None = None,
    ) -> list[RecognizedEntity]:
        import re

        entities: list[RecognizedEntity] = []
        for match in re.finditer(r"\[([A-Z_]+):([^\]]+)\]", text):
            try:
                entity_type = EntityType(match.group(1))
            except ValueError:
                continue
            if entity_types and entity_type not in entity_types:
                continue
            entities.append(
                RecognizedEntity(
                    entity_type=entity_type,
                    start=match.start(),
                    end=match.end(),
                    text=match.group(0),
                    score=1.0,
                )
            )
        return entities


class LowConfidenceNer:
    """NER stub that always returns low-confidence results (for fail-closed tests)."""

    @property
    def confidence_floor(self) -> float:
        return 0.90

    def recognize(
        self,
        text: str,
        language: str = "en",
        entity_types: list[EntityType] | None = None,
    ) -> list[RecognizedEntity]:
        if "[PERSON:" in text:
            import re

            match = re.search(r"\[PERSON:([^\]]+)\]", text)
            if match:
                return [
                    RecognizedEntity(
                        entity_type=EntityType.PERSON,
                        start=match.start(),
                        end=match.end(),
                        text=match.group(0),
                        score=0.50,
                    )
                ]
        return []


@pytest.fixture
def stub_ner() -> StubNer:
    return StubNer()


@pytest.fixture
def low_confidence_ner() -> LowConfidenceNer:
    return LowConfidenceNer()
