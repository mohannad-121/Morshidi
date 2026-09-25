"""Trusted P8 application service: integrity gate, authorization, and safe projections."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.advisor_service import AdvisorAuthorizationError, AdvisorAuthorizationService
from app.core.auth import CurrentUser
from app.decision_trace import (
    CanonicalLedgerEntry,
    IntegrityStatus,
    RedactionProfile,
    validate_entry,
    verify_integrity_hash,
)

from .errors import DecisionTraceErrorCode, DecisionTracePersistenceError
from .models import DecisionTraceSafeMetadata, DecisionTraceSafeView
from .repository import SupabaseDecisionTraceRepository


class StudentScopeRepository(Protocol):
    async def load_student_authoritative_university(
        self, student_user_id: UUID
    ) -> UUID | None: ...


class DecisionTraceService:
    """No-route service boundary over server-side persistence and P7 authorization."""

    def __init__(
        self,
        repository: SupabaseDecisionTraceRepository,
        student_scope_repository: StudentScopeRepository,
        advisor_authorization_service: AdvisorAuthorizationService,
    ) -> None:
        self._repository = repository
        self._student_scopes = student_scope_repository
        self._advisor_authorization = advisor_authorization_service

    async def append_student(
        self, principal: CurrentUser | None, entry: CanonicalLedgerEntry
    ) -> str:
        """Reject user-submitted ledger envelopes until a trusted event adapter exists.

        A verified user may request a deterministic academic operation, but neither a
        user-supplied outcome nor a matching canonical hash proves that an approved
        deterministic workflow produced it.  This method intentionally has no
        persistence path.  A future internal adapter must derive an entry from a
        concrete, verified workflow result and call the repository only after that
        result is bound to its authoritative context.
        """
        _verified_principal_uuid(principal)
        _ = entry
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.UNSUPPORTED_APPEND_AUTHORITY,
            "user-submitted decision trace envelopes are not a trusted event source",
        )

    async def append_advisor(
        self,
        principal: CurrentUser | None,
        target_student_user_id: UUID | str | None,
        entry: CanonicalLedgerEntry,
    ) -> str:
        _verified_principal_uuid(principal)
        _target_student_uuid(target_student_user_id)
        _ = entry
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.UNSUPPORTED_APPEND_AUTHORITY,
            "user-submitted advisor trace envelopes are not a trusted event source",
        )

    async def get_student_trace(
        self, principal: CurrentUser | None, ledger_entry_id: str
    ) -> DecisionTraceSafeView:
        student_id = _verified_principal_uuid(principal)
        university_id = await _student_university(self._student_scopes, student_id)
        entry = await self._load_authorized_student_entry(
            ledger_entry_id, student_id, university_id
        )
        _require_viewer_visibility(entry, RedactionProfile.STUDENT_SAFE)
        return _safe_view(entry)

    async def get_advisor_trace(
        self,
        principal: CurrentUser | None,
        target_student_user_id: UUID | str | None,
        ledger_entry_id: str,
    ) -> DecisionTraceSafeView:
        advisor_id = _verified_principal_uuid(principal)
        student_id = _target_student_uuid(target_student_user_id)
        try:
            context = await self._advisor_authorization.authorize_advisor_for_student(
                advisor_id, student_id
            )
        except AdvisorAuthorizationError as error:
            raise DecisionTracePersistenceError(
                DecisionTraceErrorCode.ACCESS_DENIED, "advisor trace authority was denied"
            ) from error
        entry = await self._load_authorized_student_entry(
            ledger_entry_id, student_id, context.university_id
        )
        _require_viewer_visibility(entry, RedactionProfile.ADVISOR_SAFE)
        return _safe_view(entry)

    async def get_institutional_individual_trace(
        self, principal: CurrentUser | None, ledger_entry_id: str
    ) -> DecisionTraceSafeView:
        """Explicit denial: institutional analysts have no individual trace/evidence interface."""
        _verified_principal_uuid(principal)
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.ACCESS_DENIED,
            "institutional viewers cannot retrieve individual decision traces",
        )

    async def _load_authorized_student_entry(
        self, ledger_entry_id: str, student_id: UUID, university_id: UUID
    ) -> CanonicalLedgerEntry:
        if not isinstance(ledger_entry_id, str) or not ledger_entry_id.strip():
            raise DecisionTracePersistenceError(
                DecisionTraceErrorCode.NOT_FOUND, "ledger identity is required"
            )
        entry = await self._repository.load_student_entry(
            ledger_entry_id=ledger_entry_id,
            student_user_id=str(student_id),
            university_id=str(university_id),
        )
        if entry is None:
            raise DecisionTracePersistenceError(
                DecisionTraceErrorCode.NOT_FOUND, "individual decision trace was not found"
            )
        _require_verified_hash(entry)
        return entry


async def _student_university(
    repository: StudentScopeRepository, student_id: UUID
) -> UUID:
    university = await repository.load_student_authoritative_university(student_id)
    if university is None:
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.ACCESS_DENIED,
            "student authoritative university scope was unavailable",
        )
    return university


def _verified_principal_uuid(principal: CurrentUser | None) -> UUID:
    """Accept only the existing Auth dependency result, never a raw request UUID."""
    if not isinstance(principal, CurrentUser):
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.AUTH_REQUIRED,
            "a principal verified by get_current_user is required",
        )
    try:
        return UUID(principal.user_id)
    except (TypeError, ValueError) as error:
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.AUTH_REQUIRED, "verified principal is invalid"
        ) from error


def _target_student_uuid(value: UUID | str | None) -> UUID:
    if value is None:
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.ACCESS_DENIED, "target student is required"
        )
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError) as error:
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.ACCESS_DENIED, "target student is invalid"
        ) from error


def _require_verified_hash(entry: CanonicalLedgerEntry) -> None:
    try:
        validate_entry(entry)
    except ValueError as error:
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.INTEGRITY_FAILURE, "decision trace domain validation failed"
        ) from error
    if verify_integrity_hash(entry) is not IntegrityStatus.VERIFIED:
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.INTEGRITY_FAILURE,
            "decision trace integrity hash does not match the Slice 1 canonical payload",
        )


def _require_viewer_visibility(
    entry: CanonicalLedgerEntry, viewer_profile: RedactionProfile
) -> None:
    """Fail closed unless the stored classification explicitly permits this viewer."""
    permitted = {
        RedactionProfile.STUDENT_SAFE: frozenset({RedactionProfile.STUDENT_SAFE}),
        RedactionProfile.ADVISOR_SAFE: frozenset(
            {RedactionProfile.STUDENT_SAFE, RedactionProfile.ADVISOR_SAFE}
        ),
    }
    if entry.redaction_profile not in permitted.get(viewer_profile, frozenset()):
        raise DecisionTracePersistenceError(
            DecisionTraceErrorCode.ACCESS_DENIED,
            "stored trace classification does not permit this viewer",
        )


def _safe_view(entry: CanonicalLedgerEntry) -> DecisionTraceSafeView:
    _require_verified_hash(entry)
    return DecisionTraceSafeView(
        metadata=DecisionTraceSafeMetadata(
            ledger_entry_id=entry.ledger_entry_id,
            decision_type=entry.decision_type,
            decision_status=entry.decision_status,
            created_at=entry.created_at,
            replay_status=entry.replay_status,
        )
    )
