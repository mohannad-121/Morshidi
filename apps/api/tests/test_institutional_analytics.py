from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.institutional_analytics.engine import build_dashboard, simulate_capacity
from app.institutional_analytics.models import (
    AnalyticsSnapshot, CourseFact, ProgramFact, SectionFact, SimulationRequest, StudentFact,
)
from app.institutional_analytics.service import (
    InstitutionalAnalyticsError, InstitutionalAnalyticsService, OfferingFacts,
)
from app.institutional_analytics.repository import SupabaseInstitutionalAnalyticsRepository
from app.mock_registration_persistence.errors import MockRegistrationPersistenceError, PersistenceFailureCode


UNIVERSITY_ID = "11111111-1111-1111-1111-111111111111"
ADMIN_ID = "22222222-2222-2222-2222-222222222222"
ADVISOR_ID = "33333333-3333-3333-3333-333333333333"
STUDENT_ID = "44444444-4444-4444-4444-444444444444"

PROGRAMS = (
    ("IT", "AI"), ("IT", "SE"), ("IT", "CS"), ("IT", "CYBER"),
    ("SCI", "MATH"), ("SCI", "PHYS"),
    ("ARTS", "ARABIC"), ("ARTS", "ENGLISH"), ("ARTS", "HISTORY"), ("ARTS", "TRANS"),
    ("BUS", "ECON"), ("BUS", "BBA"), ("BUS", "ACC"),
    ("MEDIA", "DJOURN"), ("MEDIA", "RTV"),
    ("LAW", "LAW"), ("NURS", "NURS"),
)


def snapshot(*, assigned: frozenset[str] | None = None) -> AnalyticsSnapshot:
    programs = []
    courses = []
    students = []
    for index, (faculty, major) in enumerate(PROGRAMS):
        plan_id = f"plan-{index}"
        key = f"ZU:{faculty}:{major}:P12"
        programs.append(ProgramFact(
            plan_id, key, "12", 132, faculty, f"كلية {faculty}", major, f"تخصص {major}"))
        courses.extend((
            CourseFact(f"pre-{index}", plan_id, "PRE", "متطلب", "Prerequisite", 3, 1,
                       "MAJOR_REQUIRED", "required", "not_applicable"),
            CourseFact(f"shared-{index}", plan_id, "SHARED", "مشترك", "Shared", 3, 2,
                       "MAJOR_REQUIRED", "required", "verified", (("PRE",),)),
            CourseFact(f"next-{index}", plan_id, "NEXT", "لاحق", "Next", 3, 3,
                       "MAJOR_REQUIRED", "required", "verified", (("SHARED",),)),
            CourseFact(f"review-{index}", plan_id, "REVIEW", "مراجعة", "Review", 3, 4,
                       "MAJOR_REQUIRED", "required", "unresolved", (), ("UNKNOWN101",)),
        ))
        students.append(StudentFact(
            owner_id=f"student-{index}", profile_id=f"profile-{index}", plan_id=plan_id,
            earned_credits=30, attempts=(), planned_courses=(),
        ))
    students.extend((
        StudentFact("ai-eligible", "profile-ai-eligible", "plan-0", 120,
                    (("PRE", "PASSED"),), ("SHARED",)),
        StudentFact("ai-registered", "profile-ai-registered", "plan-0", 126,
                    (("PRE", "PASSED"), ("SHARED", "IN_PROGRESS")), ()),
    ))
    return AnalyticsSnapshot(
        university_id=UNIVERSITY_ID, term_key="2026/2027-1",
        programs=tuple(programs), courses=tuple(courses), students=tuple(students),
        sections=(SectionFact("S1", "SHARED", 5, 2, 3, "OPEN"),),
        catalog_version="catalog-v17", student_state_version="students-v1",
        offering_version="offerings-v1", offering_complete=True,
        assigned_student_ids=assigned,
    )


def test_all_17_programs_and_composite_plan_identity_are_preserved():
    result = build_dashboard(snapshot(), minimum_cohort_size=3,
                             generated_at=datetime(2026, 10, 19, tzinfo=timezone.utc))
    assert len(result.programs) == 17
    assert {item.plan_key for item in result.programs} == {
        f"ZU:{faculty}:{major}:P12" for faculty, major in PROGRAMS
    }
    assert all(item.plan_number == "12" for item in result.programs)
    assert all(item.data_status in {"AVAILABLE", "SUPPRESSED"} for item in result.programs)


def test_shared_course_demand_is_distinct_and_attributed_without_cross_major_leakage():
    result = build_dashboard(snapshot(), minimum_cohort_size=3)
    shared = next(item for item in result.courses if item.course_code == "SHARED")
    assert shared.eligible_not_registered.value == 1
    assert shared.planned_need.value == 1
    assert shared.degree_path_need.value == 18
    assert shared.projected_demand.value == 18  # union; eligible/planned overlap is not double counted
    assert shared.current_registered.value == 2  # authoritative offering count wins
    assert shared.demand_capacity_gap.value == 13
    assert len(shared.demand_by_program) == 17
    assert sum(item.demand_count for item in shared.demand_by_program) == 18
    assert shared.programs_affected == sorted(item.plan_key for item in result.programs)


def test_bottleneck_capacity_and_recommendation_are_transparent_and_deterministic():
    shared = next(item for item in build_dashboard(snapshot(), minimum_cohort_size=3).courses
                  if item.course_code == "SHARED")
    assert shared.bottleneck_score == 71
    assert shared.bottleneck_level == "HIGH"
    assert shared.bottleneck_reasons == [
        "REQUIRED_CORE_COURSE", "VERIFIED_DOWNSTREAM_DEPENDENCIES",
        "PROJECTED_DEMAND_EXCEEDS_CAPACITY", "STUDENTS_AFFECTED",
    ]
    assert shared.capacity_state == "OVER_DEMAND"
    assert shared.action_recommendation == "CONSIDER_ADDITIONAL_SECTION"
    assert shared.estimated_students_helped == 13


def test_review_required_is_fail_closed_and_never_becomes_a_verified_edge():
    result = build_dashboard(snapshot(), minimum_cohort_size=3)
    review = next(item for item in result.courses if item.course_code == "REVIEW")
    assert review.prerequisite_status == "REVIEW_REQUIRED"
    assert review.eligible_not_registered.value == 0
    assert review.projection_confidence == "LOW"
    queue = next(item for item in result.review_queue if item.course_code == "REVIEW")
    assert queue.system_behavior == "FAIL_CLOSED"
    assert queue.unresolved_prerequisite_codes == ["UNKNOWN101"]
    assert queue.downstream_course_count == 0


def test_sparse_program_progress_is_suppressed_without_turning_unknown_into_zero():
    result = build_dashboard(snapshot(), minimum_cohort_size=3)
    math = next(item for item in result.programs if item.major_code == "MATH")
    assert math.student_count == 1
    assert math.data_status == "SUPPRESSED"
    assert math.average_progress_percent is None
    assert math.blocked_student_count is None
    assert all(item.student_count is None and item.status == "SUPPRESSED"
               for item in math.progress_distribution)


def test_what_if_is_non_mutating_and_returns_exact_before_after_deltas():
    result = build_dashboard(snapshot(), minimum_cohort_size=3)
    shared = next(item for item in result.courses if item.course_code == "SHARED")
    original = deepcopy(shared)
    simulated = simulate_capacity(shared, SimulationRequest(
        university_id=UNIVERSITY_ID, term_key="2026/2027-1", course_code="SHARED",
        kind="ADD_SECTION", seats=15,
    ))
    assert simulated.simulation_only is True
    assert (simulated.capacity_before, simulated.capacity_after) == (5, 20)
    assert (simulated.demand_gap_before, simulated.demand_gap_after) == (13, -2)
    assert simulated.estimated_students_helped == 13
    assert shared == original


def test_aggregate_response_contains_no_student_pii_or_diagnostic_answers():
    serialized = build_dashboard(snapshot(), minimum_cohort_size=3).model_dump_json()
    assert "owner_id" not in serialized
    assert "profile_id" not in serialized
    assert "email" not in serialized.lower()
    assert "diagnostic" not in serialized.lower()
    assert "ai-eligible" not in serialized


class FakeRepository:
    def __init__(self):
        self.assigned = frozenset({"ai-eligible"})

    async def load_assigned_student_ids(self, advisor_user_id, university_id):
        return self.assigned

    async def load_snapshot(self, university_id, term_key, **kwargs):
        base = snapshot(assigned=kwargs.get("assigned_student_ids"))
        return AnalyticsSnapshot(**{**base.__dict__, "sections": kwargs.get("sections")})


class FakeMemberships:
    async def load_active_membership(self, *, subject_user_id, university_id, role):
        if str(subject_user_id) != ADMIN_ID:
            raise MockRegistrationPersistenceError(PersistenceFailureCode.RESOURCE_NOT_FOUND, "membership")
        return SimpleNamespace(university_id=university_id, role=role)


class FakeAssignments:
    async def load_active_advisor_memberships_for_user(self, subject_user_id):
        if str(subject_user_id) == ADVISOR_ID:
            return (SimpleNamespace(university_id=UUID(UNIVERSITY_ID)),)
        return ()


class FakeOfferings:
    async def load(self, university_id, term_key):
        return OfferingFacts((SectionFact("S1", "SHARED", 5, 2, 3, "OPEN"),), "offer-v1", True)


@pytest.mark.anyio
async def test_admin_allowed_advisor_scoped_and_student_denied():
    service = InstitutionalAnalyticsService(
        FakeRepository(), FakeMemberships(), FakeAssignments(), FakeOfferings(), minimum_cohort_size=1)
    admin = await service.dashboard(ADMIN_ID, university_id=UNIVERSITY_ID, term_key="2026/2027-1")
    assert admin.role_scope == "INSTITUTION_ADMIN"
    assert admin.overview.total_active_students.value == 19
    advisor = await service.dashboard(ADVISOR_ID, university_id=UNIVERSITY_ID, term_key="2026/2027-1")
    assert advisor.role_scope == "ADVISOR_ASSIGNED"
    assert advisor.overview.total_active_students.value == 1
    with pytest.raises(InstitutionalAnalyticsError) as denied:
        await service.dashboard(STUDENT_ID, university_id=UNIVERSITY_ID, term_key="2026/2027-1")
    assert denied.value.status_code == 403


class PageResponse:
    status_code = 200
    def __init__(self, rows): self._rows = rows
    def json(self): return self._rows


class PagingClient:
    def __init__(self): self.ranges = []
    async def get(self, url, *, params, headers, timeout):
        self.ranges.append(headers["Range"])
        return PageResponse([{"id": index} for index in range(1000)] if len(self.ranges) == 1 else [{"id": 1000}])


@pytest.mark.anyio
async def test_repository_paginates_instead_of_truncating_catalog_above_postgrest_limit():
    client = PagingClient()
    repository = SupabaseInstitutionalAnalyticsRepository("https://example.supabase.co", "server-key", client)
    rows = await repository._get("study_plan_courses", {"select": "id"})
    assert len(rows) == 1001
    assert client.ranges == ["0-999", "1000-1999"]
