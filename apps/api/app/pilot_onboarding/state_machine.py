"""Deterministic state machine governing university pilot lifecycle transitions and gates."""

from __future__ import annotations

from typing import Any

from .models import (
    AcceptanceStatus,
    BlockerSeverity,
    BlockerStatus,
    PilotAcceptanceCheck,
    PilotBlocker,
    PilotMode,
    PilotRequirement,
    PilotSignoff,
    PilotStatus,
    RequirementImportance,
    RequirementStatus,
    SignoffRole,
    SignoffStatus,
    UniversityPilot,
)

# ---------------------------------------------------------------------------
# Allowable Forward & Operational State Transitions
# ---------------------------------------------------------------------------

ALLOWED_TRANSITIONS: dict[PilotStatus, set[PilotStatus]] = {
    PilotStatus.DRAFT: {
        PilotStatus.DISCOVERY,
        PilotStatus.CANCELLED,
    },
    PilotStatus.DISCOVERY: {
        PilotStatus.WAITING_FOR_UNIVERSITY_IT,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.WAITING_FOR_UNIVERSITY_IT: {
        PilotStatus.TECHNICAL_REQUIREMENTS_RECEIVED,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.TECHNICAL_REQUIREMENTS_RECEIVED: {
        PilotStatus.SANDBOX_PREPARATION,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.SANDBOX_PREPARATION: {
        PilotStatus.IDENTITY_CONFIGURATION,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.IDENTITY_CONFIGURATION: {
        PilotStatus.ACADEMIC_MAPPING,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.ACADEMIC_MAPPING: {
        PilotStatus.SECURITY_REVIEW,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.SECURITY_REVIEW: {
        PilotStatus.TECHNICAL_VALIDATION,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.TECHNICAL_VALIDATION: {
        PilotStatus.READ_ONLY_PILOT_READY,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.READ_ONLY_PILOT_READY: {
        PilotStatus.READ_ONLY_PILOT_ACTIVE,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.READ_ONLY_PILOT_ACTIVE: {
        PilotStatus.READ_ONLY_PILOT_ACCEPTANCE,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.READ_ONLY_PILOT_ACCEPTANCE: {
        PilotStatus.ACCEPTED,
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.ACCEPTED: {
        PilotStatus.WRITE_PILOT_REVIEW,
        PilotStatus.GO_LIVE_REVIEW,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.WRITE_PILOT_REVIEW: {
        PilotStatus.WRITE_ENABLED_PILOT_READY,
        PilotStatus.ACCEPTED,  # Fallback to read-only accepted
        PilotStatus.BLOCKED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.WRITE_ENABLED_PILOT_READY: {
        PilotStatus.GO_LIVE_REVIEW,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.GO_LIVE_REVIEW: {
        PilotStatus.ACCEPTED,
        PilotStatus.SUSPENDED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.BLOCKED: {
        # Can resume to previous phases or cancel
        PilotStatus.DISCOVERY,
        PilotStatus.WAITING_FOR_UNIVERSITY_IT,
        PilotStatus.TECHNICAL_REQUIREMENTS_RECEIVED,
        PilotStatus.SANDBOX_PREPARATION,
        PilotStatus.IDENTITY_CONFIGURATION,
        PilotStatus.ACADEMIC_MAPPING,
        PilotStatus.SECURITY_REVIEW,
        PilotStatus.TECHNICAL_VALIDATION,
        PilotStatus.READ_ONLY_PILOT_READY,
        PilotStatus.READ_ONLY_PILOT_ACTIVE,
        PilotStatus.READ_ONLY_PILOT_ACCEPTANCE,
        PilotStatus.WRITE_PILOT_REVIEW,
        PilotStatus.CANCELLED,
    },
    PilotStatus.SUSPENDED: {
        # Can resume to previous phases or cancel
        PilotStatus.DISCOVERY,
        PilotStatus.WAITING_FOR_UNIVERSITY_IT,
        PilotStatus.TECHNICAL_REQUIREMENTS_RECEIVED,
        PilotStatus.SANDBOX_PREPARATION,
        PilotStatus.IDENTITY_CONFIGURATION,
        PilotStatus.ACADEMIC_MAPPING,
        PilotStatus.SECURITY_REVIEW,
        PilotStatus.TECHNICAL_VALIDATION,
        PilotStatus.READ_ONLY_PILOT_READY,
        PilotStatus.READ_ONLY_PILOT_ACTIVE,
        PilotStatus.READ_ONLY_PILOT_ACCEPTANCE,
        PilotStatus.WRITE_PILOT_REVIEW,
        PilotStatus.WRITE_ENABLED_PILOT_READY,
        PilotStatus.ACCEPTED,
        PilotStatus.CANCELLED,
    },
    PilotStatus.CANCELLED: set(),  # Terminal state
}


class PilotStateMachine:
    """Evaluates and enforces deterministic gates on pilot status transitions."""

    @classmethod
    def can_transition(
        cls,
        pilot: UniversityPilot,
        target_status: PilotStatus,
        *,
        requirements: list[PilotRequirement] | None = None,
        blockers: list[PilotBlocker] | None = None,
        acceptance_checks: list[PilotAcceptanceCheck] | None = None,
        signoffs: list[PilotSignoff] | None = None,
        mapping_coverage_pct: float = 100.0,
        technical_readiness_pass: bool = True,
        write_enablement_passed: bool = False,
    ) -> tuple[bool, str | None]:
        current = PilotStatus(pilot.status) if isinstance(pilot.status, str) else pilot.status
        target_status = PilotStatus(target_status) if isinstance(target_status, str) else target_status

        # 1. Identity transition (no-op)
        if current == target_status:
            return True, None

        # 2. Check transition graph topology
        allowed_targets = ALLOWED_TRANSITIONS.get(current, set())
        if target_status not in allowed_targets:
            return (
                False,
                f"ILLEGAL_TRANSITION: Cannot transition directly from '{current.value}' to '{target_status.value}'",
            )

        # 3. Always allow transition to BLOCKED, SUSPENDED, or CANCELLED
        if target_status in {PilotStatus.BLOCKED, PilotStatus.SUSPENDED, PilotStatus.CANCELLED}:
            return True, None

        # 4. Enforce unresolved critical blockers check for forward progression
        active_blockers = blockers or []
        open_sev1 = [
            b for b in active_blockers
            if b.status in {BlockerStatus.OPEN, BlockerStatus.IN_PROGRESS} and b.severity == BlockerSeverity.SEV1
        ]
        if open_sev1 and target_status not in {PilotStatus.BLOCKED, PilotStatus.SUSPENDED, PilotStatus.CANCELLED}:
            return (
                False,
                f"UNRESOLVED_CRITICAL_BLOCKER: Blocked by SEV1 blocker '{open_sev1[0].blocker_code}': {open_sev1[0].title_ar}",
            )

        # 5. Phase-Specific Prerequisite Gates
        reqs = requirements or []

        # Gate A: To WAITING_FOR_UNIVERSITY_IT
        if target_status == PilotStatus.WAITING_FOR_UNIVERSITY_IT:
            if not pilot.discovery_intake.sis_vendor.strip():
                return False, "DISCOVERY_INTAKE_INCOMPLETE: SIS vendor and architecture must be recorded in discovery"

        # Gate B: To TECHNICAL_REQUIREMENTS_RECEIVED
        if target_status == PilotStatus.TECHNICAL_REQUIREMENTS_RECEIVED:
            received_reqs = [
                r for r in reqs
                if r.status in {RequirementStatus.RECEIVED, RequirementStatus.VALIDATED}
            ]
            if len(received_reqs) < 3:
                return False, "INSUFFICIENT_REQUIREMENTS: At least 3 requirements must be in RECEIVED or VALIDATED status"

        # Gate C: To SECURITY_REVIEW
        if target_status == PilotStatus.SECURITY_REVIEW:
            if mapping_coverage_pct < 90.0:
                return (
                    False,
                    f"MAPPING_COVERAGE_INSUFFICIENT: Required mapping coverage is >= 90%, observed {mapping_coverage_pct:.1f}%",
                )

        # Gate D: To READ_ONLY_PILOT_READY
        if target_status == PilotStatus.READ_ONLY_PILOT_READY:
            if not technical_readiness_pass:
                return False, "TECHNICAL_READINESS_FAILED: 16-point technical scorecard has unresolved FAIL items"
            # Require all REQUIRED IT requirements to be VALIDATED or NOT_APPLICABLE
            unvalidated_reqs = [
                r for r in reqs
                if r.importance == RequirementImportance.REQUIRED
                and r.status not in {RequirementStatus.VALIDATED, RequirementStatus.NOT_APPLICABLE}
            ]
            if unvalidated_reqs:
                return (
                    False,
                    f"REQUIREMENTS_UNVALIDATED: Required item '{unvalidated_reqs[0].requirement_key}' is not validated",
                )

        # Gate E: To ACCEPTED (Pilot Acceptance Gate)
        if target_status == PilotStatus.ACCEPTED:
            checks = acceptance_checks or []
            if not checks:
                return False, "ACCEPTANCE_CHECKS_EMPTY: Acceptance suite has not been executed"

            # All REQUIRED checks must be PASS or approved NOT_APPLICABLE (fail-closed on FAIL, NOT_TESTED, WARNING)
            unpassed = [
                c for c in checks
                if c.importance == RequirementImportance.REQUIRED
                and c.status not in {AcceptanceStatus.PASS, AcceptanceStatus.NOT_APPLICABLE}
            ]
            if unpassed:
                return (
                    False,
                    f"ACCEPTANCE_CHECK_FAILED: Required acceptance check '{unpassed[0].check_key}' has status '{unpassed[0].status.value}'",
                )

            # Check open SEV1 or SEV2 blockers
            open_sev2 = [
                b for b in active_blockers
                if b.status in {BlockerStatus.OPEN, BlockerStatus.IN_PROGRESS}
                and b.severity in {BlockerSeverity.SEV1, BlockerSeverity.SEV2}
            ]
            if open_sev2:
                return (
                    False,
                    f"OPEN_BLOCKERS_REMAIN: Cannot accept pilot with open {open_sev2[0].severity.value} blocker '{open_sev2[0].blocker_code}'",
                )

            # Sign-Off Gate: Required Technical and Academic sign-offs
            signs = signoffs or []
            approved_roles = {s.signoff_role for s in signs if s.status == SignoffStatus.APPROVED}
            if SignoffRole.TECHNICAL_SIGN_OFF not in approved_roles:
                return False, "SIGNOFF_MISSING: Technical Sign-Off is required before pilot acceptance"
            if SignoffRole.ACADEMIC_VALIDATION_SIGN_OFF not in approved_roles:
                return False, "SIGNOFF_MISSING: Academic Validation Sign-Off is required before pilot acceptance"

        # Gate F: To WRITE_ENABLED_PILOT_READY
        if target_status == PilotStatus.WRITE_ENABLED_PILOT_READY:
            if pilot.mode != PilotMode.WRITE_ENABLED_PILOT:
                return False, "WRITE_PILOT_MODE_REQUIRED: Pilot mode must be WRITE_ENABLED_PILOT"
            if not write_enablement_passed:
                return False, "WRITE_ENABLEMENT_GATE_FAILED: All 12 write enablement criteria must pass"

        return True, None
