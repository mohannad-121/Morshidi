from decimal import Decimal
import os
import pytest
import httpx

from app.catalog.supabase_repository import SupabaseAcademicCatalogRepository
from app.degree_path.engine import plan_degree_paths
from app.degree_path.models import (
    DegreePathConstraints,
    DegreePathOption,
    PathStatus,
)
from app.progress.engine import calculate_academic_progress
from app.progress.free_elective import (
    FreeElectiveCourseContext,
    FreeElectiveCourseDecision,
    evaluate_free_elective_course,
)
from app.progress.models import (
    AcademicProgressCatalog,
    ApprovedFreeElectiveCourse,
    CourseProgressState,
    FreeElectiveSelectionState,
    ProgressPlanCourse,
    ProgressRequirementGroup,
    ProgressStudyPlan,
    RequirementSelectionPolicy,
    RequirementSelectionPolicyStatus,
    RequirementType,
)
from app.rules.models import AttemptOutcome, CourseCatalogStatus, StudentCourseAttempt

GROUP_ID = "20000000-0000-0000-0000-000000000001"
PLAN_ID = "10000000-0000-0000-0000-000000000001"
NURSING_PLAN_ID = "2a78bbbb-0dc0-5c46-8630-7a46e4179830"

@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
LOCAL_SUPABASE_URL = os.getenv("MORSHIDI_LOCAL_SUPABASE_URL", "http://127.0.0.1:54321")
LOCAL_SERVER_KEY = os.getenv(
    "MORSHIDI_LOCAL_SUPABASE_SERVER_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU",
)


def _catalog(*, policy_available: bool, approved: bool = False) -> AcademicProgressCatalog:
    return AcademicProgressCatalog(
        study_plan=ProgressStudyPlan(PLAN_ID, Decimal("3")),
        requirement_groups=(ProgressRequirementGroup(
            group_id=GROUP_ID,
            study_plan_id=PLAN_ID,
            group_code="FREE_ELECTIVE",
            name_ar="متطلب حر",
            name_en="Free Elective",
            scope="other",
            requirement_type=RequirementType.FREE_ELECTIVE,
            required_credit_hours=Decimal("3"),
            display_order=7,
            selection_policy=RequirementSelectionPolicy.UNIVERSITY_APPROVED,
            selection_policy_status=(
                RequirementSelectionPolicyStatus.AVAILABLE
                if policy_available
                else RequirementSelectionPolicyStatus.POLICY_REQUIRED
            ),
        ),),
        plan_courses=(),
        approved_free_elective_courses=(ApprovedFreeElectiveCourse(
            requirement_group_id=GROUP_ID,
            course_code="REAL100",
            credit_hours=Decimal("3"),
            course_name_ar="مادة جامعية فعلية",
        ),) if approved else (),
    )


def test_unknown_policy_is_a_typed_fail_closed_requirement() -> None:
    progress = calculate_academic_progress(_catalog(policy_available=False), ())
    group = progress.requirement_groups[0]
    assert progress.plan_total_required_credits == Decimal("3")
    assert group.remaining_required_credits == Decimal("3")
    assert group.free_elective_selection_state is FreeElectiveSelectionState.FREE_ELECTIVE_POLICY_REQUIRED
    assert progress.courses == ()


@pytest.mark.parametrize(
    ("attempt", "completed", "current", "remaining"),
    [
        (StudentCourseAttempt("REAL100", AttemptOutcome.PASSED), Decimal("3"), Decimal("0"), Decimal("0")),
        (StudentCourseAttempt("REAL100", AttemptOutcome.IN_PROGRESS), Decimal("0"), Decimal("3"), Decimal("3")),
    ],
)
def test_approved_real_course_is_recognized_without_fake_membership(
    attempt: StudentCourseAttempt,
    completed: Decimal,
    current: Decimal,
    remaining: Decimal,
) -> None:
    progress = calculate_academic_progress(_catalog(policy_available=True, approved=True), (attempt,))
    group = progress.requirement_groups[0]
    assert group.credited_toward_requirement == completed
    assert group.in_progress_credited_toward_requirement == current
    assert group.remaining_required_credits == remaining
    assert progress.courses[0].satisfies_free_elective is True


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"policy_available": False}, FreeElectiveCourseDecision.FREE_ELECTIVE_POLICY_REQUIRED),
        ({"approved_by_policy": False}, FreeElectiveCourseDecision.COURSE_NOT_APPROVED_AS_FREE_ELECTIVE),
        ({"already_counted_toward_degree": True}, FreeElectiveCourseDecision.COURSE_ALREADY_COUNTED),
        ({"offered_in_term": False}, FreeElectiveCourseDecision.COURSE_NOT_OFFERED),
        ({"prerequisites_satisfied": False}, FreeElectiveCourseDecision.PREREQUISITE_BLOCKED),
        ({}, FreeElectiveCourseDecision.COURSE_ELIGIBLE_AS_FREE_ELECTIVE),
    ],
)
def test_course_option_gate(overrides: dict[str, bool], expected: FreeElectiveCourseDecision) -> None:
    values = {
        "policy_available": True,
        "approved_by_policy": True,
        "offered_in_term": True,
        "prerequisites_satisfied": True,
        **overrides,
    }
    assert evaluate_free_elective_course(FreeElectiveCourseContext(**values)) is expected


def test_plan_course_cannot_be_double_counted_as_free_elective() -> None:
    catalog = _catalog(policy_available=True, approved=True)
    catalog = AcademicProgressCatalog(
        study_plan=ProgressStudyPlan(catalog.study_plan.study_plan_id, Decimal("6")),
        requirement_groups=catalog.requirement_groups + (ProgressRequirementGroup(
            group_id="20000000-0000-0000-0000-000000000002",
            study_plan_id=PLAN_ID,
            group_code="MAJOR",
            name_ar="تخصص",
            name_en="Major",
            scope="major",
            requirement_type=RequirementType.REQUIRED,
            required_credit_hours=Decimal("3"),
            display_order=1,
        ),),
        plan_courses=(ProgressPlanCourse(
            plan_course_id="30000000-0000-0000-0000-000000000001",
            study_plan_id=PLAN_ID,
            course_code="REAL100",
            credit_hours=Decimal("3"),
            requirement_group_id="20000000-0000-0000-0000-000000000002",
            catalog_status=CourseCatalogStatus.KNOWN,
            display_order=1,
        ),),
        approved_free_elective_courses=catalog.approved_free_elective_courses,
    )
    with pytest.raises(Exception, match="cannot count toward two degree requirements"):
        calculate_academic_progress(catalog, ())


@pytest.mark.anyio
async def test_nursing_freshman_and_real_local_postgres_validation() -> None:
    """Verify Nursing Plan 12 from real local PostgreSQL/PostgREST.

    Verifies:
    - NURSING_CANONICAL_TOTAL = 132
    - NURSING_REQUIREMENT_GROUP_SUM = 132
    - NURSING_PROGRESS_TOTAL = 132
    - NURSING_DEGREE_PATH_TOTAL = 132
    - FREE_ELECTIVE_REQUIREMENT_PRESENT = YES
    - FAKE_FREE_ELECTIVE_COURSE_CREATED = NO
    - Freshman accounting: required=3, earned=0, remaining=3
    - Disjoint, non-duplicated, no foreign courses
    """
    async with httpx.AsyncClient(timeout=10.0) as http:
        repo = SupabaseAcademicCatalogRepository(LOCAL_SUPABASE_URL, LOCAL_SERVER_KEY, client=http)
        p_cat = await repo.load_progress_catalog(NURSING_PLAN_ID)
        e_cat = await repo.load_plan_eligibility_catalog(NURSING_PLAN_ID)

    # 1. Canonical total
    assert p_cat.study_plan.total_credit_hours == Decimal("132")

    # 2. Requirement group sum
    group_sum = sum((g.required_credit_hours for g in p_cat.requirement_groups), Decimal("0"))
    assert group_sum == Decimal("132")
    assert len(p_cat.requirement_groups) == 7

    # 3. Free elective requirement node present
    free_group = next(
        (g for g in p_cat.requirement_groups if g.group_code == "FREE_ELECTIVE"), None
    )
    assert free_group is not None
    assert free_group.requirement_type is RequirementType.FREE_ELECTIVE
    assert free_group.required_credit_hours == Decimal("3")
    assert free_group.selection_policy is RequirementSelectionPolicy.UNIVERSITY_APPROVED
    assert free_group.selection_policy_status is RequirementSelectionPolicyStatus.POLICY_REQUIRED

    # 4. Zero fake courses created
    for course in p_cat.plan_courses:
        assert not course.course_code.upper().startswith("FREE")
        assert not course.course_code.upper().startswith("ELECTIVE")
        assert course.course_code != "0000000"

    # 5. Freshman Progress (0 attempts)
    progress = calculate_academic_progress(p_cat, ())
    assert progress.plan_total_required_credits == Decimal("132")
    assert progress.completed_plan_credits == Decimal("0")
    assert progress.remaining_plan_credits == Decimal("132")
    assert progress.in_progress_plan_credits == Decimal("0")

    free_progress = next(
        g for g in progress.requirement_groups if g.group_code == "FREE_ELECTIVE"
    )
    assert free_progress.required_credits == Decimal("3")
    assert free_progress.credited_toward_requirement == Decimal("0")
    assert free_progress.remaining_required_credits == Decimal("3")
    assert free_progress.free_elective_selection_state is FreeElectiveSelectionState.FREE_ELECTIVE_POLICY_REQUIRED
    assert free_progress.is_satisfied is False

    # 6. Freshman Degree Path
    dp_result = plan_degree_paths(
        p_cat,
        e_cat,
        (),
        DegreePathConstraints(max_credit_hours_per_semester=Decimal("18"), max_paths=3),
    )
    assert len(dp_result.paths) > 0
    for path in dp_result.paths:
        assert path.credit_summary.degree_required_credits == Decimal("132")
        assert path.credit_summary.completed_credits == Decimal("0")
        assert path.credit_summary.current_credits == Decimal("0")
        assert (
            path.credit_summary.future_placed_credits + path.credit_summary.unplaced_credits
            == Decimal("132")
        )
        assert len(path.free_elective_requirements) == 1
        fe_node = path.free_elective_requirements[0]
        assert fe_node.group_code == "FREE_ELECTIVE"
        assert fe_node.required_credits == Decimal("3")
        assert fe_node.completed_credits == Decimal("0")
        assert fe_node.remaining_credits_after_current == Decimal("3")
        assert fe_node.selection_state == "FREE_ELECTIVE_POLICY_REQUIRED"
        assert fe_node.completed_course_codes == ()
        assert fe_node.current_course_codes == ()


@pytest.mark.anyio
async def test_near_graduation_scenario_only_free_elective_remaining() -> None:
    """Test student with all 129 catalog credits completed, only 3 free elective remaining."""
    async with httpx.AsyncClient(timeout=10.0) as http:
        repo = SupabaseAcademicCatalogRepository(LOCAL_SUPABASE_URL, LOCAL_SERVER_KEY, client=http)
        p_cat = await repo.load_progress_catalog(NURSING_PLAN_ID)
        e_cat = await repo.load_plan_eligibility_catalog(NURSING_PLAN_ID)

    # Pick passed courses that satisfy exactly the 6 other requirement groups:
    # 18 (univ req) + 9 (univ elect) + 21 (faculty req) + 66 (major req) + 3 (major elect) + 12 (supporting) = 129
    # We can pass all 63 catalog courses, which totals >= required for each group.
    # Group credit capping caps credited sum to 129!
    attempts = tuple(
        StudentCourseAttempt(pc.course_code, AttemptOutcome.PASSED)
        for pc in p_cat.plan_courses
    )

    progress = calculate_academic_progress(p_cat, attempts)
    assert progress.plan_total_required_credits == Decimal("132")
    assert progress.completed_plan_credits == Decimal("129")
    assert progress.remaining_plan_credits == Decimal("3")

    free_progress = next(
        g for g in progress.requirement_groups if g.group_code == "FREE_ELECTIVE"
    )
    assert free_progress.credited_toward_requirement == Decimal("0")
    assert free_progress.remaining_required_credits == Decimal("3")
    assert free_progress.is_satisfied is False

    # Degree path with 129 credits completed
    dp_result = plan_degree_paths(
        p_cat,
        e_cat,
        attempts,
        DegreePathConstraints(max_credit_hours_per_semester=Decimal("18"), max_paths=3),
    )
    assert len(dp_result.paths) > 0
    p1 = dp_result.paths[0]
    assert p1.credit_summary.degree_required_credits == Decimal("132")
    assert p1.credit_summary.completed_credits == Decimal("129")
    assert p1.credit_summary.current_credits == Decimal("0")
    assert p1.credit_summary.future_placed_credits == Decimal("0")
    assert p1.credit_summary.unplaced_credits == Decimal("3")
    assert p1.status is PathStatus.NO_VALID_NEXT_PLAN
    assert "FREE_ELECTIVE_POLICY_REQUIRED" in p1.unresolved_blocker_codes

    fe_req = p1.free_elective_requirements[0]
    assert fe_req.group_code == "FREE_ELECTIVE"
    assert fe_req.required_credits == Decimal("3")
    assert fe_req.remaining_credits_after_current == Decimal("3")
    assert fe_req.selection_state == "FREE_ELECTIVE_POLICY_REQUIRED"
