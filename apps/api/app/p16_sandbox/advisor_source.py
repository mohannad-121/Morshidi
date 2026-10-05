"""Authenticated sandbox academic-state source for the student advisor."""

from __future__ import annotations

from app.p16_sandbox.persona import resolve_sandbox_persona
from app.p16_sandbox.sis_adapter import SandboxSISAdapter
from app.p16_sandbox.tenant import SANDBOX_INSTITUTION_ID
from app.student.models import StudentAcademicState


class SandboxAdvisorStudentSource:
    """Load an allowlisted synthetic persona through the canonical P15 adapter."""

    def __init__(self, adapter: SandboxSISAdapter) -> None:
        self._adapter = adapter

    async def load_student_academic_state(
        self, owner_user_id: str, persona_id: str,
    ) -> StudentAcademicState:
        resolved = resolve_sandbox_persona(persona_id, SANDBOX_INSTITUTION_ID)
        record = await self._adapter.get_canonical_record(resolved)
        if record.institution_id != SANDBOX_INSTITUTION_ID or record.student_id != resolved:
            raise PermissionError("Sandbox academic record scope mismatch")
        return StudentAcademicState(
            profile_id=f"sandbox:{resolved}",
            owner_user_id=owner_user_id,
            study_plan_id=record.plan_id,
            reported_cumulative_gpa=None,
            reported_gpa_scale=None,
            reported_earned_credit_hours=record.earned_credits,
            attempts=record.attempts,
        )
