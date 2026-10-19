"""Generic SIS Adapter protocol declaring capability-negotiated integration methods."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .capabilities import SISCapability
from .models import (
    ChangeBatch,
    HealthResult,
    NormalizedAuthResult,
    NormalizedCourse,
    NormalizedEnrollment,
    NormalizedGradeAttempt,
    NormalizedOffering,
    NormalizedStudent,
    NormalizedStudyPlan,
    NormalizedTerm,
)


@runtime_checkable
class SISAdapter(Protocol):
    """Protocol implemented by all SIS integrations (FakeUniversity, GenericREST, Banner, etc.)."""

    @property
    def provider_type(self) -> str:
        """Unique provider type identifier (e.g. 'fake_university', 'generic_rest')."""
        ...

    @property
    def capabilities(self) -> set[SISCapability]:
        """Declared set of supported integration capabilities."""
        ...

    async def health_check(self) -> HealthResult:
        """Probe external SIS connectivity, responsiveness, and service health."""
        ...

    async def authenticate_student(self, student_id: str, password: str) -> NormalizedAuthResult:
        """Authenticate student credentials against external SIS."""
        ...

    async def get_student_profile(self, student_id: str, token: str) -> NormalizedStudent:
        """Fetch authoritative student profile."""
        ...

    async def get_current_courses(self, student_id: str, token: str) -> list[NormalizedCourse]:
        """Fetch courses currently active or available to student."""
        ...

    async def get_grades(self, student_id: str, token: str) -> list[NormalizedGradeAttempt]:
        """Fetch student course attempts, outcomes, and grades."""
        ...

    async def get_enrollments(self, student_id: str, token: str) -> list[NormalizedEnrollment]:
        """Fetch active term section enrollments."""
        ...

    async def get_academic_plan(self, student_id: str, token: str) -> NormalizedStudyPlan:
        """Fetch student's authoritative curriculum / study plan structure."""
        ...

    async def get_terms(self) -> list[NormalizedTerm]:
        """Fetch academic terms / calendar from SIS."""
        ...

    async def get_course_offerings(self, term_code: str) -> list[NormalizedOffering]:
        """Fetch schedule and section offerings for the given term."""
        ...

    async def get_registration_context(self, student_id: str, token: str) -> dict[str, Any]:
        """Fetch authoritative registration window and status context."""
        ...

    async def preview_registration(
        self, student_id: str, token: str, section_ids: list[str]
    ) -> dict[str, Any]:
        """Non-mutating preview of section registration validation."""
        ...

    async def register_sections(
        self, student_id: str, token: str, section_ids: list[str], idempotency_key: str
    ) -> dict[str, Any]:
        """Authoritative section registration mutation."""
        ...

    async def drop_sections(
        self, student_id: str, token: str, section_id: str, idempotency_key: str
    ) -> dict[str, Any]:
        """Authoritative section drop mutation."""
        ...

    async def get_cursor_or_change_token(self) -> str | None:
        """Return latest SIS state cursor or change token for incremental sync."""
        ...

    async def fetch_changes_since(self, cursor: str | None) -> ChangeBatch:
        """Fetch incremental changes occurred since the specified cursor."""
        ...

