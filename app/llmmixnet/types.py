"""Core types for LLMMixNet v0 (SHE-563 ADR §3, §4, §6)."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class DataType(enum.Enum):
    """Source dataset type attached to every orchestrator prompt call.

    Drives per-data-type policy dispatch in Layer2Redactor (ADR §4.3).
    UNKNOWN triggers the strictest policy (full NER) by default (ADR §4.3).
    """

    UNKNOWN = "unknown"
    TRANSACTIONS = "transactions"
    CALENDARS = "calendars"
    JOURNAL = "journal"
    LOCATION = "location"
    OUTCOMES = "outcomes"


class EntityType(enum.Enum):
    """PII entity types recognized by the NER layer (ADR §1, §4.3).

    Covers the v0 floor: standard Presidio types + three shenas-domain
    extensions (MERCHANT_NAME, ACCOUNT_ID, H3_HEX_R6).
    """

    PERSON = "PERSON"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    PHONE_NUMBER = "PHONE_NUMBER"
    CREDIT_CARD = "CREDIT_CARD"
    IBAN_CODE = "IBAN_CODE"
    IP_ADDRESS = "IP_ADDRESS"
    LOCATION = "LOCATION"
    DATE_TIME = "DATE_TIME"
    URL = "URL"
    ORGANIZATION = "ORGANIZATION"
    US_SSN = "US_SSN"
    MEDICAL_LICENSE = "MEDICAL_LICENSE"
    IN_AADHAAR = "IN_AADHAAR"
    # shenas-domain extensions
    MERCHANT_NAME = "MERCHANT_NAME"
    ACCOUNT_ID = "ACCOUNT_ID"
    H3_HEX_R6 = "H3_HEX_R6"


class PrivacyState(enum.Enum):
    """Three-state traffic-light privacy indicator (ADR §3.5).

    GREEN  — full Layer 2 + Layer 4 healthy + per-session rotation.
    AMBER  — degraded but still oblivious (see AmberCause for specifics).
    RED    — direct-TLS override active; raw IP + raw content to provider.
    """

    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class AmberCause(enum.Enum):
    """Named causes for the AMBER state (ADR §4.6).

    Multiple causes may apply simultaneously; each is listed in the tooltip.
    """

    PERSISTENT_PSEUDONYM = "persistent_pseudonym"
    COVERAGE_DEGRADED = "coverage_degraded"
    SINGLE_RELAY = "single_relay"
    RESTORE_FAILED = "restore_failed"
    TTL_EXTENDED = "ttl_extended"


@dataclass(frozen=True)
class RecognizedEntity:
    """A single PII entity found by the NER layer."""

    entity_type: EntityType
    start: int
    end: int
    text: str
    score: float


@dataclass(frozen=True)
class Placeholder:
    """A stable per-session placeholder for a recognized entity."""

    entity_type: EntityType
    index: int

    def __str__(self) -> str:
        return f"<{self.entity_type.value}_{self.index}>"

    @classmethod
    def from_string(cls, token: str) -> Placeholder:
        """Parse '<ENTITY_TYPE_n>' back into a Placeholder."""
        inner = token.strip("<>")
        last_underscore = inner.rfind("_")
        if last_underscore == -1:
            raise ValueError(f"Invalid placeholder token: {token!r}")
        entity_name = inner[:last_underscore]
        index = int(inner[last_underscore + 1 :])
        return cls(entity_type=EntityType(entity_name), index=index)


@dataclass
class RedactionResult:
    """Output of Layer2Redactor.redact()."""

    redacted_text: str
    mapping_id: str
    privacy_state: PrivacyState
    amber_causes: list[AmberCause] = field(default_factory=list)
    entities_by_type: dict[str, int] = field(default_factory=dict)


@dataclass
class RestorationResult:
    """Output of Layer2Redactor.restore()."""

    restored_text: str
    privacy_state: PrivacyState
    amber_causes: list[AmberCause] = field(default_factory=list)
    placeholders_remaining: int = 0
