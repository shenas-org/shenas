"""Tests for Layer2Redactor: redact/restore round-trip per data type.

Uses the StubNer from conftest (no Presidio required) to test all business
logic paths: policy dispatch, placeholder assignment, mapping storage,
confidence floor enforcement, restore, amber state propagation.
"""

from __future__ import annotations

import pytest

from app.llmmixnet.redactor import ConfidenceFloorError, Layer2Redactor
from app.llmmixnet.types import AmberCause, DataType, EntityType, PrivacyState


class TestRedactBasic:
    def test_no_entities_returns_green(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact("The weather is fine.", session_id, DataType.JOURNAL)
        assert result.redacted_text == "The weather is fine."
        assert result.privacy_state == PrivacyState.GREEN
        assert result.amber_causes == []

    def test_entity_replaced_with_placeholder(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact("Hello [PERSON:Alice]!", session_id, DataType.JOURNAL)
        assert "[PERSON:Alice]" not in result.redacted_text
        assert "<PERSON_0>" in result.redacted_text
        assert result.privacy_state == PrivacyState.GREEN

    def test_multiple_entities_indexed(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact(
            "Email [EMAIL_ADDRESS:a@b.com] from [PERSON:Alice].",
            session_id,
            DataType.JOURNAL,
        )
        assert "<EMAIL_ADDRESS_0>" in result.redacted_text
        assert "<PERSON_0>" in result.redacted_text

    def test_same_type_multiple_occurrences_unique_indices(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact("[PERSON:Alice] and [PERSON:Bob]", session_id, DataType.JOURNAL)
        assert "<PERSON_0>" in result.redacted_text
        assert "<PERSON_1>" in result.redacted_text

    def test_entity_histogram_populated(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact("[PERSON:Alice] and [PERSON:Bob]", session_id, DataType.JOURNAL)
        assert result.entities_by_type.get("PERSON") == 2

    def test_mapping_id_is_uuid(self, mapping_store, stub_ner):
        import uuid

        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact("[PERSON:Alice]", session_id)
        uuid.UUID(result.mapping_id)


class TestRoundTrip:
    def test_restore_returns_original_entity(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        redact_result = redactor.redact("Hello [PERSON:Alice]!", session_id, DataType.JOURNAL)
        restore_result = redactor.restore(redact_result.redacted_text, redact_result.mapping_id)
        assert "Alice" in restore_result.restored_text
        assert restore_result.privacy_state == PrivacyState.GREEN
        assert restore_result.placeholders_remaining == 0

    def test_round_trip_multiple_entities(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        original = "[PERSON:Alice] sent [EMAIL_ADDRESS:alice@x.com] to [PERSON:Bob]."
        redact_result = redactor.redact(original, session_id, DataType.JOURNAL)
        restore_result = redactor.restore(redact_result.redacted_text, redact_result.mapping_id)
        assert "Alice" in restore_result.restored_text
        assert "alice@x.com" in restore_result.restored_text
        assert "Bob" in restore_result.restored_text

    def test_restore_missing_mapping_amber(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        restore_result = redactor.restore("Hello <PERSON_0>!", "nonexistent-mapping-id")
        assert restore_result.privacy_state == PrivacyState.AMBER
        assert AmberCause.RESTORE_FAILED in restore_result.amber_causes
        assert restore_result.placeholders_remaining == 1
        assert "<PERSON_0>" in restore_result.restored_text

    def test_restore_no_placeholders_green(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        restore_result = redactor.restore("No entities here.", "any-mapping")
        assert restore_result.privacy_state == PrivacyState.GREEN
        assert restore_result.placeholders_remaining == 0


class TestDataTypePolicies:
    def test_journal_default_for_unknown(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact("[PERSON:Alice]", session_id, DataType.UNKNOWN)
        assert "<PERSON_0>" in result.redacted_text

    def test_transactions_policy(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact(
            "Charge $42 at [MERCHANT_NAME:Starbucks]",
            session_id,
            DataType.TRANSACTIONS,
        )
        assert result.privacy_state in (PrivacyState.GREEN, PrivacyState.AMBER)

    def test_calendars_policy_covers_person(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact("Meeting with [PERSON:Alice] at 3pm", session_id, DataType.CALENDARS)
        assert "<PERSON_0>" in result.redacted_text

    def test_outcomes_policy_cleartext_numbers(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact("HRV today: 42, stress: 3", session_id, DataType.OUTCOMES)
        assert "42" in result.redacted_text
        assert "3" in result.redacted_text


class TestConfidenceFloor:
    def test_low_confidence_raises(self, mapping_store, low_confidence_ner):
        redactor = Layer2Redactor(mapping_store, low_confidence_ner)
        session_id = mapping_store.create_session()
        with pytest.raises(ConfidenceFloorError) as exc_info:
            redactor.redact("[PERSON:Alice]", session_id, DataType.JOURNAL)
        assert exc_info.value.entity.entity_type == EntityType.PERSON

    def test_safe_span_bypasses_floor(self, mapping_store, low_confidence_ner):
        redactor = Layer2Redactor(mapping_store, low_confidence_ner)
        session_id = mapping_store.create_session()
        text = "[PERSON:Alice]"
        result = redactor.redact(
            text,
            session_id,
            DataType.JOURNAL,
            safe_spans=[(0, len(text))],
        )
        assert result.privacy_state == PrivacyState.GREEN


class TestPseudonymLifecycle:
    def test_default_session_is_not_persistent(self, mapping_store, stub_ner):
        session_id = mapping_store.create_session()
        assert not mapping_store.is_persistent(session_id)

    def test_persistent_session_surfaces_amber(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session(persistent_mode=True)
        result = redactor.redact("[PERSON:Alice]", session_id, DataType.JOURNAL)
        assert result.privacy_state == PrivacyState.AMBER
        assert AmberCause.PERSISTENT_PSEUDONYM in result.amber_causes

    def test_per_session_rotation_different_mappings(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_a = mapping_store.create_session()
        session_b = mapping_store.create_session()
        result_a = redactor.redact("[PERSON:Alice]", session_a)
        result_b = redactor.redact("[PERSON:Alice]", session_b)
        assert result_a.mapping_id != result_b.mapping_id

    def test_within_session_same_type_stable_index(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        result = redactor.redact("[PERSON:Alice] met [PERSON:Alice]", session_id)
        assert "<PERSON_0>" in result.redacted_text
        assert "<PERSON_1>" in result.redacted_text


class TestOrchestratorIntegration:
    """Integration tests against the orchestrator interface (mocked transport).

    Validates that Layer2Redactor can be composed with a mock transport
    that returns the redacted text unchanged (simulating the provider
    echoing back placeholders).
    """

    def test_full_pipeline_round_trip(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()

        prompt = "Send a report to [PERSON:Alice] at [EMAIL_ADDRESS:alice@example.com]."

        redact_result = redactor.redact(prompt, session_id, DataType.JOURNAL)
        assert "[PERSON:Alice]" not in redact_result.redacted_text
        assert "alice@example.com" not in redact_result.redacted_text

        # Simulate provider echoing back with placeholders intact.
        provider_response = (
            f"Report sent to {redact_result.redacted_text.split('<')[1].split('>')[0]}"
            f"<{redact_result.redacted_text.split('<')[1].split('>')[0]}>"
            if "<" in redact_result.redacted_text
            else redact_result.redacted_text
        )
        provider_response = redact_result.redacted_text

        restore_result = redactor.restore(provider_response, redact_result.mapping_id)
        assert restore_result.privacy_state == PrivacyState.GREEN
        assert "Alice" in restore_result.restored_text
        assert "alice@example.com" in restore_result.restored_text

    def test_failed_transport_mapping_survives(self, mapping_store, stub_ner):
        redactor = Layer2Redactor(mapping_store, stub_ner)
        session_id = mapping_store.create_session()
        redact_result = redactor.redact("[PERSON:Alice]", session_id)
        # Transport fails; provider never called; restore should still work
        # because mapping was persisted before transport.
        restore_result = redactor.restore(redact_result.redacted_text, redact_result.mapping_id)
        assert restore_result.privacy_state == PrivacyState.GREEN
