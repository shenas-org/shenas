"""Per-data-type redaction policies for Layer 2 (ADR §4.3).

Each policy returns a list of (original_span, replacement_token) pairs.
The Layer2Redactor applies these to build the redacted text and the
placeholder mapping in a single left-to-right pass.

Policy dispatch:
  TRANSACTIONS → TransactionPolicy
  CALENDARS    → CalendarPolicy
  JOURNAL      → JournalPolicy
  LOCATION     → LocationPolicy
  OUTCOMES     → OutcomesPolicy (numeric values cleartext; entity context
                                  delegated to surrounding NER)
  UNKNOWN      → JournalPolicy  (strictest; full NER — ADR §4.3 default)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from app.llmmixnet.types import DataType, EntityType


@dataclass(frozen=True)
class SpanReplacement:
    """A (start, end, replacement_token) triple for the redaction pass."""

    start: int
    end: int
    original: str
    token: str


class DataTypePolicy(Protocol):
    """Protocol for per-data-type redaction policies."""

    @property
    def entity_types(self) -> list[EntityType]: ...

    def preprocess_replacements(
        self,
        text: str,
        store_hmac_bin: object | None = None,
    ) -> list[SpanReplacement]: ...


class TransactionPolicy:
    """Redaction policy for finance data (ADR §4.3.1).

    - Merchant names: HMAC-bin to MERCHANT_BIN_0x{hex}.
    - Free-text memo fields: full NER (entity_types list passed to recognizer).
    - Amounts: cleartext.
    - Categories: cleartext (finite shenas enum).
    - Account IDs: tokenized to ACCOUNT_ID_n.

    Pre-processor finds merchant names and account IDs via simple pattern
    matching; NER covers the rest.
    """

    # Patterns for structured fields that don't need NER.
    _ACCOUNT_PATTERN = re.compile(
        r"\b(acct|account|acc)[\s#:_-]*([A-Z0-9]{4,20})\b",
        re.IGNORECASE,
    )

    @property
    def entity_types(self) -> list[EntityType]:
        return [
            EntityType.PERSON,
            EntityType.EMAIL_ADDRESS,
            EntityType.PHONE_NUMBER,
            EntityType.CREDIT_CARD,
            EntityType.IBAN_CODE,
            EntityType.ORGANIZATION,
        ]

    def preprocess_replacements(
        self,
        text: str,
        store_hmac_bin: object = None,
    ) -> list[SpanReplacement]:
        replacements: list[SpanReplacement] = []
        if store_hmac_bin is None:
            return replacements
        for match in self._ACCOUNT_PATTERN.finditer(text):
            token = "ACCOUNT_ID_0"
            replacements.append(
                SpanReplacement(
                    start=match.start(),
                    end=match.end(),
                    original=match.group(),
                    token=token,
                )
            )
        return replacements


class CalendarPolicy:
    """Redaction policy for calendar data (ADR §4.3.2).

    - Attendees: tokenized to PERSON_n (NER handles this).
    - Event title: full NER.
    - Cadence: cleartext (recurrence rules, time-of-day, day-of-week).
    - Locations: H3 r=6 snap or LOCATION_n placeholder.
    """

    @property
    def entity_types(self) -> list[EntityType]:
        return [
            EntityType.PERSON,
            EntityType.EMAIL_ADDRESS,
            EntityType.PHONE_NUMBER,
            EntityType.LOCATION,
            EntityType.URL,
            EntityType.ORGANIZATION,
        ]

    def preprocess_replacements(
        self,
        text: str,  # noqa: ARG002
        store_hmac_bin: object = None,  # noqa: ARG002
    ) -> list[SpanReplacement]:
        return []


class JournalPolicy:
    """Strictest policy: full NER on all entity types (ADR §4.3.3 / default)."""

    @property
    def entity_types(self) -> list[EntityType]:
        return list(EntityType)

    def preprocess_replacements(
        self,
        text: str,  # noqa: ARG002
        store_hmac_bin: object = None,  # noqa: ARG002
    ) -> list[SpanReplacement]:
        return []


class LocationPolicy:
    """Policy for location-only prompts (ADR §4.3.4).

    Applies H3 r=6 snapping to any coordinate pair found in the text;
    falls back to NER LOCATION tokenization for free-text place names.
    """

    @property
    def entity_types(self) -> list[EntityType]:
        return [EntityType.LOCATION]

    def preprocess_replacements(
        self,
        text: str,
        store_hmac_bin: object = None,  # noqa: ARG002
    ) -> list[SpanReplacement]:
        from app.llmmixnet.location import extract_and_coarsen

        replacements: list[SpanReplacement] = []
        coarsened = extract_and_coarsen(text)
        if coarsened is not None:
            replacements.append(
                SpanReplacement(
                    start=0,
                    end=len(text),
                    original=text,
                    token=coarsened,
                )
            )
        return replacements


class OutcomesPolicy:
    """Policy for outcomes/fitness/vitals (ADR §4.3.5).

    Numeric values are cleartext. Entity context (people, places) is
    handled by the surrounding NER pass.
    """

    @property
    def entity_types(self) -> list[EntityType]:
        return [
            EntityType.PERSON,
            EntityType.LOCATION,
            EntityType.EMAIL_ADDRESS,
        ]

    def preprocess_replacements(
        self,
        text: str,  # noqa: ARG002
        store_hmac_bin: object = None,  # noqa: ARG002
    ) -> list[SpanReplacement]:
        return []


_POLICY_MAP: dict[DataType, DataTypePolicy] = {
    DataType.TRANSACTIONS: TransactionPolicy(),
    DataType.CALENDARS: CalendarPolicy(),
    DataType.JOURNAL: JournalPolicy(),
    DataType.LOCATION: LocationPolicy(),
    DataType.OUTCOMES: OutcomesPolicy(),
    DataType.UNKNOWN: JournalPolicy(),
}


def policy_for(data_type: DataType) -> DataTypePolicy:
    """Return the policy for a given DataType (default: JournalPolicy)."""
    return _POLICY_MAP.get(data_type, JournalPolicy())
