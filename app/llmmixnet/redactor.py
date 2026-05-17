"""Layer 2 redactor: PII detection + reversible pseudonym mapping (ADR §4).

Layer2Redactor.redact(text, session_id, data_type) → RedactionResult
Layer2Redactor.restore(text, mapping_id) → RestorationResult

Fail-closed semantics (ADR §3.3):
  - If NER confidence drops below the floor for any recognized entity,
    the call raises ConfidenceFloorError unless the caller has explicitly
    marked the span as safe (per-request override, ADR §3.3).
  - If the mapping store cannot write (storage failure), raises MappingWriteError.
  - Restore failures surface the response with placeholders intact + amber
    indicator; they do not raise.
"""

from __future__ import annotations

import re
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.llmmixnet.mapping import MappingStore

from app.llmmixnet.ner import NerRecognizer, PresidioRecognizer
from app.llmmixnet.policy import SpanReplacement, policy_for
from app.llmmixnet.types import (
    AmberCause,
    DataType,
    EntityType,
    Placeholder,
    PrivacyState,
    RecognizedEntity,
    RedactionResult,
    RestorationResult,
)

_PLACEHOLDER_RE = re.compile(r"<([A-Z_]+)_(\d+)>")


class ConfidenceFloorError(Exception):
    """Raised when an entity's NER score is below the confidence floor.

    Maps to the "block + surface could-not-redact-safely" outcome in
    ADR §3.3 error table row 1.
    """

    def __init__(self, entity: RecognizedEntity, floor: float) -> None:
        self.entity = entity
        self.floor = floor
        super().__init__(
            f"NER confidence {entity.score:.2f} < floor {floor:.2f} "
            f"for entity type {entity.entity_type.value!r} at [{entity.start}:{entity.end}]. "
            "Either annotate the span as safe or use the direct-TLS override."
        )


class MappingWriteError(Exception):
    """Raised when the mapping store cannot persist a row (ADR §3.3 row 2)."""


class Layer2Redactor:
    """PII redaction with reversible per-session mapping (ADR §4).

    Requires:
      - mapping_store: MappingStore (handles DuckDB + key material)
      - ner_recognizer: any NerRecognizer (defaults to PresidioRecognizer)
    """

    def __init__(
        self,
        mapping_store: MappingStore,
        ner_recognizer: NerRecognizer | None = None,
    ) -> None:
        self._store = mapping_store
        self._ner = ner_recognizer or PresidioRecognizer()

    def redact(
        self,
        text: str,
        session_id: str,
        data_type: DataType = DataType.UNKNOWN,
        safe_spans: list[tuple[int, int]] | None = None,
    ) -> RedactionResult:
        """Redact PII from text, storing the mapping under a fresh mapping_id.

        Parameters
        ----------
        text:
            The prompt text to redact.
        session_id:
            Existing session from MappingStore.create_session().
        data_type:
            Dataset origin; drives per-type policy dispatch (ADR §4.3).
        safe_spans:
            List of (start, end) byte spans the user has explicitly marked
            safe to send (per-request override, ADR §3.3). Entities within
            these spans bypass the confidence floor check and are kept as-is.
        """
        policy = policy_for(data_type)
        safe_spans = safe_spans or []

        preprocess_replacements = policy.preprocess_replacements(
            text,
            store_hmac_bin=self._store.hmac_bin,
        )

        ner_entities = self._ner.recognize(
            text,
            entity_types=policy.entity_types,
        )

        amber_causes: list[AmberCause] = []
        if self._store.is_persistent(session_id):
            amber_causes.append(AmberCause.PERSISTENT_PSEUDONYM)

        confidence_floor = self._ner.confidence_floor
        for entity in ner_entities:
            if _is_in_safe_spans(entity.start, entity.end, safe_spans):
                continue
            if entity.score < confidence_floor:
                amber_causes.append(AmberCause.COVERAGE_DEGRADED)
                raise ConfidenceFloorError(entity, confidence_floor)

        replacements = _merge_replacements(preprocess_replacements, ner_entities)

        mapping_id = str(uuid.uuid4())
        entity_counters: dict[EntityType, int] = {}
        entity_type_histogram: dict[str, int] = {}
        final_replacements: list[tuple[int, int, str]] = []

        for span in replacements:
            if isinstance(span, SpanReplacement):
                final_replacements.append((span.start, span.end, span.token))
                continue
            entity: RecognizedEntity = span
            counter = entity_counters.get(entity.entity_type, 0)
            entity_counters[entity.entity_type] = counter + 1
            placeholder = Placeholder(entity_type=entity.entity_type, index=counter)
            token = str(placeholder)
            try:
                self._store.store_mapping(
                    session_id=session_id,
                    mapping_id=mapping_id,
                    placeholder=token,
                    entity_text=entity.text,
                    entity_type=entity.entity_type.value,
                )
            except Exception as exc:
                raise MappingWriteError(f"Failed to store mapping for {token!r}: {exc}") from exc
            final_replacements.append((entity.start, entity.end, token))
            type_name = entity.entity_type.value
            entity_type_histogram[type_name] = entity_type_histogram.get(type_name, 0) + 1

        redacted = _apply_replacements(text, final_replacements)

        self._store.touch_session(session_id)

        privacy_state = PrivacyState.AMBER if amber_causes else PrivacyState.GREEN
        return RedactionResult(
            redacted_text=redacted,
            mapping_id=mapping_id,
            privacy_state=privacy_state,
            amber_causes=amber_causes,
            entities_by_type=entity_type_histogram,
        )

    def restore(self, text: str, mapping_id: str) -> RestorationResult:
        """Replace placeholders in text with original entities from the mapping.

        Never raises on missing mappings — returns amber + placeholders intact
        (ADR §3.3 row "Restore fails").
        """
        amber_causes: list[AmberCause] = []
        placeholders_remaining = 0

        def _replace(match: re.Match) -> str:
            nonlocal placeholders_remaining
            token = match.group(0)
            original = self._store.retrieve_entity(mapping_id, token)
            if original is None:
                placeholders_remaining += 1
                return token
            return original

        restored = _PLACEHOLDER_RE.sub(_replace, text)

        if placeholders_remaining > 0:
            amber_causes.append(AmberCause.RESTORE_FAILED)

        privacy_state = PrivacyState.AMBER if amber_causes else PrivacyState.GREEN
        return RestorationResult(
            restored_text=restored,
            privacy_state=privacy_state,
            amber_causes=amber_causes,
            placeholders_remaining=placeholders_remaining,
        )


def _is_in_safe_spans(start: int, end: int, safe_spans: list[tuple[int, int]]) -> bool:
    return any(ss <= start and end <= se for ss, se in safe_spans)


def _merge_replacements(
    preprocess: list[SpanReplacement],
    ner_entities: list[RecognizedEntity],
) -> list[SpanReplacement | RecognizedEntity]:
    """Merge pre-processor replacements and NER entities, sorted by start offset.

    Overlapping spans are resolved by keeping the first (leftmost) replacement
    and skipping any later span that overlaps it.
    """
    combined: list[SpanReplacement | RecognizedEntity] = []
    combined.extend(preprocess)
    combined.extend(ner_entities)
    combined.sort(key=lambda item: item.start)

    merged: list[SpanReplacement | RecognizedEntity] = []
    last_end = 0
    for item in combined:
        if item.start < last_end:
            continue
        merged.append(item)
        last_end = item.end
    return merged


def _apply_replacements(text: str, replacements: list[tuple[int, int, str]]) -> str:
    """Apply a sorted list of (start, end, token) replacements to text."""
    replacements.sort(key=lambda r: r[0])
    result: list[str] = []
    cursor = 0
    for start, end, token in replacements:
        if start < cursor:
            continue
        result.append(text[cursor:start])
        result.append(token)
        cursor = end
    result.append(text[cursor:])
    return "".join(result)
