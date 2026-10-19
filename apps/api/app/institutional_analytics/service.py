"""Authorization and read-only orchestration for production institutional analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from app.advisor_persistence.errors import AdvisorPersistenceError
from app.advisor_persistence.repository import SupabaseAdvisorAssignmentRepository
from app.mock_registration_persistence.errors import MockRegistrationPersistenceError
from app.mock_registration_persistence.repository import SupabaseMockRegistrationRepository

from .engine import build_dashboard, simulate_capacity
from .models import DashboardResponse, SectionFact, SimulationRequest, SimulationResponse
from .repository import InstitutionalAnalyticsRepository, InstitutionalAnalyticsRepositoryError


class InstitutionalAnalyticsError(RuntimeError):
    def __init__(self, code: str, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class OfferingFacts:
    sections: tuple[SectionFact, ...] | None
    source_version: str | None
    complete: bool
    resolved_term_key: str | None = None


class InstitutionalOfferingProvider(Protocol):
    async def load(self, university_id: str, term_key: str) -> OfferingFacts: ...


class UnavailableInstitutionalOfferingProvider:
    async def load(self, university_id: str, term_key: str) -> OfferingFacts:
        return OfferingFacts(None, None, False)


class CurrentUniversityOfferingProvider:
    """Read-only adapter over the existing Fake University institutional offering contract."""

    def __init__(self, contract_client: Any, configured_university_id: str | None) -> None:
        self._client = contract_client
        self._university_id = configured_university_id

    async def load(self, university_id: str, term_key: str) -> OfferingFacts:
        if self._university_id and university_id != self._university_id:
            return OfferingFacts(None, None, False)
        try:
            calendar = await self._client.current_term()
            current = calendar.get("currentTerm") or calendar.get("current_term") or calendar
            current_key = str(current.get("code") or current.get("term") or "") if isinstance(current, dict) else ""
            if not current_key or term_key not in {"CURRENT", current_key}:
                return OfferingFacts(None, None, False)
            raw = await self._client.live_offerings(current_key)
            manifest = await self._client.manifest()
        except Exception:
            return OfferingFacts(None, None, False)
        sections: list[SectionFact] = []
        for row in raw:
            if not isinstance(row, dict):
                continue
            code = str(row.get("course_code") or row.get("courseCode") or "").strip()
            section_id = str(row.get("id") or row.get("section_id") or "").strip()
            if not code or not section_id:
                continue
            capacity = _integer(row.get("capacity"))
            enrolled = _integer(row.get("enrolled"))
            available = _integer(row.get("available"))
            if available is None and capacity is not None and enrolled is not None:
                available = max(0, capacity - enrolled)
            sections.append(SectionFact(
                section_id=section_id, course_code=code, capacity=capacity,
                enrolled=enrolled, available=available,
                status=str(row.get("status")) if row.get("status") is not None else None,
            ))
        version = str(manifest.get("schema_version") or manifest.get("version") or current_key)
        return OfferingFacts(tuple(sections), version, True, current_key)


class InstitutionalAnalyticsService:
    def __init__(
        self, repository: InstitutionalAnalyticsRepository,
        memberships: SupabaseMockRegistrationRepository,
        advisor_assignments: SupabaseAdvisorAssignmentRepository,
        offering_provider: InstitutionalOfferingProvider | None = None,
        *, minimum_cohort_size: int = 3,
    ) -> None:
        self._repository = repository
        self._memberships = memberships
        self._advisor_assignments = advisor_assignments
        self._offerings = offering_provider or UnavailableInstitutionalOfferingProvider()
        self._minimum_cohort_size = minimum_cohort_size

    async def access(self, subject: str) -> list[dict[str, str]]:
        """List only the caller's active institutional scopes; never infer authority from claims."""
        scopes: dict[str, str] = {}
        try:
            analyst = await self._memberships.load_active_memberships_for_user(
                subject_user_id=UUID(subject), role="INSTITUTIONAL_ANALYST")
            for membership in analyst:
                scopes[str(membership.university_id)] = "INSTITUTION_ADMIN"
            advisor = await self._advisor_assignments.load_active_advisor_memberships_for_user(UUID(subject))
            for membership in advisor:
                scopes.setdefault(str(membership.university_id), "ADVISOR_ASSIGNED")
        except (MockRegistrationPersistenceError, AdvisorPersistenceError, ValueError) as error:
            raise InstitutionalAnalyticsError(
                "INSTITUTIONAL_ANALYTICS_UNAVAILABLE", 503, "Institutional authorization is unavailable") from error
        if not scopes:
            raise InstitutionalAnalyticsError(
                "INSTITUTIONAL_ACCESS_DENIED", 403, "Institutional analytics access is denied")
        return [{"university_id": key, "role_scope": scopes[key]} for key in sorted(scopes)]

    async def _scope(self, subject: str, university_id: str) -> frozenset[str] | None:
        try:
            await self._memberships.load_active_membership(
                subject_user_id=UUID(subject), university_id=UUID(university_id),
                role="INSTITUTIONAL_ANALYST",
            )
            return None
        except (MockRegistrationPersistenceError, ValueError):
            pass
        try:
            memberships = await self._advisor_assignments.load_active_advisor_memberships_for_user(UUID(subject))
            if any(str(item.university_id) == university_id for item in memberships):
                return await self._repository.load_assigned_student_ids(subject, university_id)
        except (AdvisorPersistenceError, InstitutionalAnalyticsRepositoryError, ValueError) as error:
            raise InstitutionalAnalyticsError(
                "INSTITUTIONAL_ANALYTICS_UNAVAILABLE", 503, "Institutional authorization is unavailable") from error
        raise InstitutionalAnalyticsError(
            "INSTITUTIONAL_ACCESS_DENIED", 403, "Institutional analytics access is denied")

    async def dashboard(
        self, subject: str, *, university_id: str, term_key: str,
        faculty: str | None = None, major: str | None = None, plan_key: str | None = None,
    ) -> DashboardResponse:
        assigned = await self._scope(subject, university_id)
        offerings = await self._offerings.load(university_id, term_key)
        effective_term_key = offerings.resolved_term_key or term_key
        try:
            snapshot = await self._repository.load_snapshot(
                university_id, effective_term_key, sections=offerings.sections,
                offering_version=offerings.source_version, offering_complete=offerings.complete,
                assigned_student_ids=assigned,
            )
            return build_dashboard(
                snapshot, faculty=faculty, major=major, plan_key=plan_key,
                minimum_cohort_size=self._minimum_cohort_size,
            )
        except (InstitutionalAnalyticsRepositoryError, ValueError) as error:
            raise InstitutionalAnalyticsError(
                "INSTITUTIONAL_ANALYTICS_UNAVAILABLE", 503, "Institutional analytics are unavailable") from error

    async def simulate(self, subject: str, request: SimulationRequest) -> SimulationResponse:
        dashboard = await self.dashboard(
            subject, university_id=request.university_id, term_key=request.term_key)
        course = next((item for item in dashboard.courses if item.course_code == request.course_code), None)
        if course is None:
            raise InstitutionalAnalyticsError("COURSE_NOT_FOUND", 404, "Course is not available in this scope")
        try:
            return simulate_capacity(course, request)
        except ValueError as error:
            raise InstitutionalAnalyticsError("INVALID_SIMULATION", 422, str(error)) from error


def _integer(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
