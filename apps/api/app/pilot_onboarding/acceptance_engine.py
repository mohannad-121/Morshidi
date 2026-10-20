"""Evaluation engine for pilot acceptance criteria and structured report generation."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from .models import (
    AcceptanceStatus,
    BlockerSeverity,
    BlockerStatus,
    PilotAcceptanceCheck,
    PilotBlocker,
    PilotMode,
    PilotReport,
    PilotSignoff,
    PilotStatus,
    RequirementImportance,
    SignoffRole,
    SignoffStatus,
    UniversityPilot,
)


class PilotAcceptanceEngine:
    """Evaluates acceptance criteria suites and generates deterministic pilot acceptance reports."""

    @classmethod
    def evaluate_suite(
        cls,
        pilot: UniversityPilot,
        checks: list[PilotAcceptanceCheck],
        *,
        blockers: list[PilotBlocker] | None = None,
        signoffs: list[PilotSignoff] | None = None,
    ) -> dict[str, Any]:
        """Evaluate the overall acceptance status based on deterministic rules."""
        active_blockers = blockers or []
        signs = signoffs or []

        total_checks = len(checks)
        passed_checks = sum(1 for c in checks if c.status == AcceptanceStatus.PASS)
        warning_checks = sum(1 for c in checks if c.status == AcceptanceStatus.WARNING)
        failed_checks = sum(1 for c in checks if c.status == AcceptanceStatus.FAIL)
        not_tested_checks = sum(1 for c in checks if c.status == AcceptanceStatus.NOT_TESTED)
        na_checks = sum(1 for c in checks if c.status == AcceptanceStatus.NOT_APPLICABLE)

        # 1. Check unfulfilled REQUIRED checks
        unfulfilled_required = [
            c for c in checks
            if c.importance == RequirementImportance.REQUIRED
            and c.status not in {AcceptanceStatus.PASS, AcceptanceStatus.NOT_APPLICABLE}
        ]

        # 2. Check open blockers
        open_sev1_or_sev2 = [
            b for b in active_blockers
            if b.status in {BlockerStatus.OPEN, BlockerStatus.IN_PROGRESS}
            and b.severity in {BlockerSeverity.SEV1, BlockerSeverity.SEV2}
        ]

        # 3. Check signoffs
        approved_roles = {s.signoff_role for s in signs if s.status == SignoffStatus.APPROVED}
        has_tech_signoff = SignoffRole.TECHNICAL_SIGN_OFF in approved_roles
        has_acad_signoff = SignoffRole.ACADEMIC_VALIDATION_SIGN_OFF in approved_roles

        # Deterministic decision logic
        if unfulfilled_required or open_sev1_or_sev2:
            overall: Literal["PASS", "FAIL", "WARNING"] = "FAIL"
            can_accept = False
            recommendation: Literal["ACCEPTED", "ACCEPTED_WITH_WARNINGS", "BLOCKED"] = "BLOCKED"
        elif warning_checks > 0 or not (has_tech_signoff and has_acad_signoff):
            overall = "WARNING"
            can_accept = has_tech_signoff and has_acad_signoff
            recommendation = "ACCEPTED_WITH_WARNINGS" if can_accept else "BLOCKED"
        else:
            overall = "PASS"
            can_accept = has_tech_signoff and has_acad_signoff
            recommendation = "ACCEPTED" if can_accept else "BLOCKED"

        return {
            "overall_status": overall,
            "can_accept": can_accept,
            "recommendation": recommendation,
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "warning_checks": warning_checks,
            "failed_checks": failed_checks,
            "not_tested_checks": not_tested_checks,
            "not_applicable_checks": na_checks,
            "unfulfilled_required_count": len(unfulfilled_required),
            "open_critical_blockers_count": len(open_sev1_or_sev2),
            "has_technical_signoff": has_tech_signoff,
            "has_academic_signoff": has_acad_signoff,
        }

    @classmethod
    def generate_report(
        cls,
        pilot: UniversityPilot,
        checks: list[PilotAcceptanceCheck],
        *,
        university_name: str,
        technical_readiness: dict[str, Any],
        mapping_coverage: dict[str, float],
        sync_health: dict[str, Any],
        security_status: dict[str, Any],
        blockers: list[PilotBlocker] | None = None,
        signoffs: list[PilotSignoff] | None = None,
    ) -> PilotReport:
        """Construct the formal structured acceptance report."""
        eval_result = cls.evaluate_suite(
            pilot,
            checks,
            blockers=blockers,
            signoffs=signoffs,
        )

        active_blockers = [b.model_dump(mode="json") for b in (blockers or []) if b.status != BlockerStatus.RESOLVED]
        formatted_signoffs = [s.model_dump(mode="json") for s in (signoffs or [])]

        return PilotReport(
            pilot_id=pilot.id,
            university_id=pilot.university_id,
            university_name=university_name,
            pilot_name=pilot.pilot_name,
            mode=pilot.mode,
            status=pilot.status,
            technical_readiness=technical_readiness,
            mapping_coverage=mapping_coverage,
            sync_health=sync_health,
            security_status=security_status,
            acceptance_results=eval_result,
            open_blockers=active_blockers,
            signoffs=formatted_signoffs,
            final_recommendation=eval_result["recommendation"],
        )
