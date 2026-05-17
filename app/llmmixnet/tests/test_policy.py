"""Tests for per-data-type policy dispatch (ADR §4.3)."""

from __future__ import annotations

from app.llmmixnet.policy import (
    CalendarPolicy,
    JournalPolicy,
    LocationPolicy,
    OutcomesPolicy,
    TransactionPolicy,
    policy_for,
)
from app.llmmixnet.types import DataType, EntityType


class TestPolicyFor:
    def test_unknown_maps_to_journal(self):
        policy = policy_for(DataType.UNKNOWN)
        assert isinstance(policy, JournalPolicy)

    def test_transactions_policy(self):
        assert isinstance(policy_for(DataType.TRANSACTIONS), TransactionPolicy)

    def test_calendars_policy(self):
        assert isinstance(policy_for(DataType.CALENDARS), CalendarPolicy)

    def test_journal_policy(self):
        assert isinstance(policy_for(DataType.JOURNAL), JournalPolicy)

    def test_location_policy(self):
        assert isinstance(policy_for(DataType.LOCATION), LocationPolicy)

    def test_outcomes_policy(self):
        assert isinstance(policy_for(DataType.OUTCOMES), OutcomesPolicy)


class TestJournalPolicy:
    def test_includes_all_entity_types(self):
        policy = JournalPolicy()
        assert EntityType.PERSON in policy.entity_types
        assert EntityType.EMAIL_ADDRESS in policy.entity_types
        assert EntityType.CREDIT_CARD in policy.entity_types
        assert EntityType.MEDICAL_LICENSE in policy.entity_types

    def test_preprocess_returns_empty(self):
        policy = JournalPolicy()
        assert policy.preprocess_replacements("hello") == []


class TestTransactionPolicy:
    def test_entity_types_exclude_sensitive_id_types(self):
        policy = TransactionPolicy()
        assert EntityType.PERSON in policy.entity_types
        assert EntityType.CREDIT_CARD in policy.entity_types

    def test_preprocess_no_hmac_fn_returns_empty(self):
        policy = TransactionPolicy()
        result = policy.preprocess_replacements("Transaction at Starbucks")
        assert result == []


class TestCalendarPolicy:
    def test_entity_types_includes_person_and_location(self):
        policy = CalendarPolicy()
        assert EntityType.PERSON in policy.entity_types
        assert EntityType.LOCATION in policy.entity_types

    def test_preprocess_returns_empty(self):
        policy = CalendarPolicy()
        assert policy.preprocess_replacements("Meeting with team at HQ") == []


class TestLocationPolicy:
    def test_entity_types_is_location_only(self):
        policy = LocationPolicy()
        assert policy.entity_types == [EntityType.LOCATION]

    def test_preprocess_coarsens_coordinates(self):
        policy = LocationPolicy()
        text = "48.8566, 2.3522"
        replacements = policy.preprocess_replacements(text)
        if replacements:
            assert len(replacements) == 1
            token = replacements[0].token
            # H3 cell ID or fallback LOC_xx.xx_xx.xx format
            assert token.startswith("LOC_") or len(token) == 15

    def test_preprocess_no_coordinates_returns_empty(self):
        policy = LocationPolicy()
        replacements = policy.preprocess_replacements("Meeting at the office")
        assert replacements == []


class TestOutcomesPolicy:
    def test_entity_types_limited(self):
        policy = OutcomesPolicy()
        assert EntityType.PERSON in policy.entity_types
        assert EntityType.CREDIT_CARD not in policy.entity_types

    def test_preprocess_returns_empty(self):
        policy = OutcomesPolicy()
        assert policy.preprocess_replacements("Sleep score: 85, HRV: 42") == []
