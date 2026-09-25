"""P8 Slice 2B trusted persistence and safe retrieval boundary."""

from .errors import DecisionTraceErrorCode, DecisionTracePersistenceError
from .models import DecisionTraceSafeMetadata, DecisionTraceSafeView
from .p6_outbox_mapper import (
    P6DecisionTraceOutboxEvent,
    TrustedP6OutboxProjection,
    map_verified_mock_registration_submit,
)
from .repository import SupabaseDecisionTraceRepository
from .service import DecisionTraceService

__all__ = [
    "DecisionTraceErrorCode",
    "DecisionTracePersistenceError",
    "DecisionTraceSafeView",
    "DecisionTraceSafeMetadata",
    "SupabaseDecisionTraceRepository",
    "DecisionTraceService",
    "P6DecisionTraceOutboxEvent",
    "TrustedP6OutboxProjection",
    "map_verified_mock_registration_submit",
]
