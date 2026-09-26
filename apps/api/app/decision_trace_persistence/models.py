"""Conservative, allowlisted service return types for individual trace retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from datetime import datetime

from app.decision_trace.registries import DecisionStatus, DecisionType, ReplayStatus


@dataclass(frozen=True, slots=True)
class DecisionTraceSafeMetadata:
    """Stable, non-free-form metadata approved for the local individual projection.

    Opaque scope, tenant, student, engine, policy, source, limitation, outcome, and
    evidence fields are deliberately absent until an approved disclosure contract
    classifies them for each viewer.
    """

    ledger_entry_id: str
    decision_type: DecisionType
    decision_status: DecisionStatus
    created_at: datetime
    replay_status: ReplayStatus


@dataclass(frozen=True, slots=True)
class DecisionTraceSafeView:
    """Minimum individual projection; evidence is not projected in this local slice."""

    metadata: DecisionTraceSafeMetadata
