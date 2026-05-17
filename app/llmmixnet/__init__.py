"""LLMMixNet: privacy-preserving LLM routing (SHE-563 ADR).

v0 scope: Layer 2 (PII redaction with reversible mapping) + Layer 4 (OHTTP
transport, in app/llmmixnet/transport/) + the orchestrator that sequences them.
Layer 1, Layer 3, and Layer 4 paranoid-mode (Nym) are out of scope for v0.
"""

from app.llmmixnet.redactor import Layer2Redactor
from app.llmmixnet.types import (
    DataType,
    EntityType,
    PrivacyState,
    RedactionResult,
    RestorationResult,
)

__all__ = [
    "DataType",
    "EntityType",
    "Layer2Redactor",
    "PrivacyState",
    "RedactionResult",
    "RestorationResult",
]
