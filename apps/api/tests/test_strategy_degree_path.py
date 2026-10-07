"""Tests for strategy-bound degree path course allocation (deterministic course plans)."""

from decimal import Decimal
import pytest

from app.degree_path.credit_timeline import (
    AcademicTerm,
    ComparisonMode,
    CreditComparisonScenario,
    CreditTerm,
    CreditTimeline,
    compare_credit_timelines,
    simulate_credit_timeline,
)
from app.degree_path.strategy_allocator import (
    StrategyCourse,
    StrategyDegreePath,
    StrategyTerm,
    allocate_strategy_degree_path,
)
from app.progress.models import (
    AcademicProgressCatalog,
    ProgressPlanCourse,
    ProgressRequirementGroup,
    ProgressStudyPlan,
    RequirementType,
)
from app.rules.models import (
    AttemptOutcome,
    CanTakeCatalog,
    CourseCatalogStatus,
    CourseIdentity,
    DependencyGroup,
    DependencyType,
    PlanCourseRule,
    PrerequisiteLogicStatus,
    StudentCourseAttempt,
)

PLAN_ID = "test-plan-1"


def _make_catalogs():
    study_plan = ProgressStudyPlan(study_plan_id=PLAN_ID, total_credit_hours=Decimal("132"))
    groups = (
        ProgressRequirementGroup(
            group_id="g-uni-req",
            study_plan_id=PLAN_ID,
            group_code="UNI_REQ",
            name_ar="متطلبات جامعة إجبارية",
            name_en="University Required",
            scope="UNIVERSITY",
            requirement_type=RequirementType.REQUIRED,
            required_credit_hours=Decimal("18"),
            display_order=1,
        ),
        ProgressRequirementGroup(
            group_id="g-maj-req",
            study_plan_id=PLAN_ID,
            group_code="MAJ_REQ",
            name_ar="متطلبات تخصص إجبارية",
            name_en="Major Required",
            scope="MAJOR",
            requirement_type=RequirementType.REQUIRED,
            required_credit_hours=Decimal("60"),
            display_order=2,
        ),
        ProgressRequirementGroup(
            group_id="g-maj-elec",
            study_plan_id=PLAN_ID,
            group_code="MAJ_ELEC",
            name_ar="متطلبات تخصص اختيارية",
            name_en="Major Elective",
            scope="MAJOR",
            requirement_type=RequirementType.ELECTIVE,
            required_credit_hours=Decimal("12"),
            display_order=3,
        ),
    )

    # 12 courses of 3 credits, plus two 0-credit courses, plus two 1-credit courses
    plan_courses = []
    rules = []
    identities = []

    # Two 0-credit courses
    for code, name in [("0000001", "ندوة"), ("0000002", "خدمة مجتمع")]:
        plan_courses.append(
            ProgressPlanCourse(
                plan_course_id=f"pc-{code}",
                study_plan_id=PLAN_ID,
                requirement_group_id="g-uni-req",
                course_code=code,
                catalog_status=CourseCatalogStatus.KNOWN,
                credit_hours=Decimal("0"),
                display_order=len(plan_courses) + 1,
                course_name_ar=name,
                course_name_en=f"Course {code}",
            )
        )
        rules.append(
            PlanCourseRule(
                course_code=code,
                prerequisite_logic_status=PrerequisiteLogicStatus.NOT_APPLICABLE,
                dependency_groups=(),
                target_name_en=f"Course {code}",
            )
        )
        identities.append(CourseIdentity(code, CourseCatalogStatus.KNOWN))

    # Twelve 3-credit courses
    for i in range(1, 13):
        code = f"11000{i:02d}"
        gid = "g-maj-req" if i <= 8 else "g-maj-elec"
        plan_courses.append(
            ProgressPlanCourse(
                plan_course_id=f"pc-{code}",
                study_plan_id=PLAN_ID,
                requirement_group_id=gid,
                course_code=code,
                catalog_status=CourseCatalogStatus.KNOWN,
                credit_hours=Decimal("3"),
                display_order=len(plan_courses) + 1,
                course_name_ar=f"مادة {i}",
                course_name_en=f"Major Course {i}",
            )
        )
        rules.append(
            PlanCourseRule(
                course_code=code,
                prerequisite_logic_status=PrerequisiteLogicStatus.NOT_APPLICABLE,
                dependency_groups=(),
                target_name_en=f"Major Course {i}",
            )
        )
        identities.append(CourseIdentity(code, CourseCatalogStatus.KNOWN))

    progress_catalog = AcademicProgressCatalog(
        study_plan=study_plan,
        requirement_groups=groups,
        plan_courses=tuple(plan_courses),
    )
    eligibility_catalog = CanTakeCatalog(
        study_plan_id=PLAN_ID,
        plan_courses=tuple(rules),
        courses=tuple(identities),
        complete_plan_credits=True,
    )
    return progress_catalog, eligibility_catalog


def test_allocate_strategy_degree_path_fastest_exact_target():
    progress_catalog, eligibility_catalog = _make_catalogs()
    student_attempts = ()

    # FASTEST scenario with 2 terms of 18 credits each = 36 total
    timeline = CreditTimeline(
        policy_version="TEST_V1",
        total_required_credits=Decimal("132"),
        earned_credits=Decimal("96"),
        initial_remaining_credits=Decimal("36"),
        regular_load=Decimal("18"),
        summer_enabled=False,
        summer_load=Decimal("0"),
        terms=(
            CreditTerm(2026, AcademicTerm.FIRST_SEMESTER, Decimal("18"), Decimal("18")),
            CreditTerm(2026, AcademicTerm.SECOND_SEMESTER, Decimal("18"), Decimal("0")),
        ),
        regular_semester_count=2,
        summer_count=0,
        completion_year=2026,
        completion_term=AcademicTerm.SECOND_SEMESTER,
        assumptions=(),
        warnings=(),
    )
    scenario = CreditComparisonScenario(
        scenario_id="FASTEST_TEST",
        mode=ComparisonMode.FASTEST,
        timeline=timeline,
        total_modeled_terms=2,
        workload_indicator="HIGH",
        preference_match=True,
    )

    path = allocate_strategy_degree_path(
        progress_catalog,
        eligibility_catalog,
        student_attempts,
        scenario,
        reported_earned_credit_hours=Decimal("96"),
    )

    assert path.strategy == "FASTEST"
    assert path.status == "COMPLETE"
    assert path.total_target_credits == Decimal("36")
    assert path.total_allocated_credits == Decimal("36")
    assert path.unallocated_credit_hours == Decimal("0")
    assert len(path.terms) == 2

    # Term 1: 18 credits (6 courses of 3cr + 2 courses of 0cr = 8 courses)
    term1 = path.terms[0]
    assert term1.target_credit_hours == Decimal("18")
    assert term1.allocated_credit_hours == Decimal("18")
    assert sum(c.credit_hours for c in term1.courses) == Decimal("18")
    # Both zero-credit required courses are included in term 1
    zero_cr = [c for c in term1.courses if c.credit_hours == Decimal("0")]
    assert len(zero_cr) == 2

    # Term 2: 18 credits (6 courses of 3cr)
    term2 = path.terms[1]
    assert term2.target_credit_hours == Decimal("18")
    assert term2.allocated_credit_hours == Decimal("18")
    assert sum(c.credit_hours for c in term2.courses) == Decimal("18")

    # No duplicate courses across terms
    term1_codes = {c.course_code for c in term1.courses}
    term2_codes = {c.course_code for c in term2.courses}
    assert term1_codes.isdisjoint(term2_codes)


def test_allocate_strategy_degree_path_balanced_exact_target():
    progress_catalog, eligibility_catalog = _make_catalogs()
    student_attempts = ()

    # BALANCED scenario with 3 terms of 12 credits each = 36 total
    timeline = CreditTimeline(
        policy_version="TEST_V1",
        total_required_credits=Decimal("132"),
        earned_credits=Decimal("96"),
        initial_remaining_credits=Decimal("36"),
        regular_load=Decimal("12"),
        summer_enabled=False,
        summer_load=Decimal("0"),
        terms=(
            CreditTerm(2026, AcademicTerm.FIRST_SEMESTER, Decimal("12"), Decimal("24")),
            CreditTerm(2026, AcademicTerm.SECOND_SEMESTER, Decimal("12"), Decimal("12")),
            CreditTerm(2027, AcademicTerm.FIRST_SEMESTER, Decimal("12"), Decimal("0")),
        ),
        regular_semester_count=3,
        summer_count=0,
        completion_year=2027,
        completion_term=AcademicTerm.FIRST_SEMESTER,
        assumptions=(),
        warnings=(),
    )
    scenario = CreditComparisonScenario(
        scenario_id="BALANCED_TEST",
        mode=ComparisonMode.BALANCED,
        timeline=timeline,
        total_modeled_terms=3,
        workload_indicator="MODERATE",
        preference_match=True,
    )

    path = allocate_strategy_degree_path(
        progress_catalog,
        eligibility_catalog,
        student_attempts,
        scenario,
        reported_earned_credit_hours=Decimal("96"),
    )

    assert path.strategy == "BALANCED"
    assert path.status == "COMPLETE"
    assert path.total_target_credits == Decimal("36")
    assert path.total_allocated_credits == Decimal("36")
    assert path.unallocated_credit_hours == Decimal("0")
    assert len(path.terms) == 3

    for term in path.terms:
        assert term.target_credit_hours == Decimal("12")
        assert term.allocated_credit_hours == Decimal("12")
        assert sum(c.credit_hours for c in term.courses) == Decimal("12")

    all_planned = [c.course_code for t in path.terms for c in t.courses]
    assert len(all_planned) == len(set(all_planned)), "No duplicate courses allowed"


def test_allocate_strategy_degree_path_partial_when_insufficient_courses():
    progress_catalog, eligibility_catalog = _make_catalogs()
    # Assume 10 of the 12 three-credit courses were already passed
    already_passed = tuple(
        StudentCourseAttempt(course_code=f"11000{i:02d}", outcome=AttemptOutcome.PASSED)
        for i in range(1, 11)
    )

    # Student requests 18 credits in Term 1, but only 2 three-credit courses (6cr) remain
    timeline = CreditTimeline(
        policy_version="TEST_V1",
        total_required_credits=Decimal("132"),
        earned_credits=Decimal("126"),
        initial_remaining_credits=Decimal("6"),
        regular_load=Decimal("18"),
        summer_enabled=False,
        summer_load=Decimal("0"),
        terms=(
            CreditTerm(2026, AcademicTerm.FIRST_SEMESTER, Decimal("18"), Decimal("0")),
        ),
        regular_semester_count=1,
        summer_count=0,
        completion_year=2026,
        completion_term=AcademicTerm.FIRST_SEMESTER,
        assumptions=(),
        warnings=(),
    )
    scenario = CreditComparisonScenario(
        scenario_id="PARTIAL_TEST",
        mode=ComparisonMode.FASTEST,
        timeline=timeline,
        total_modeled_terms=1,
        workload_indicator="HIGH",
        preference_match=True,
    )

    path = allocate_strategy_degree_path(
        progress_catalog,
        eligibility_catalog,
        already_passed,
        scenario,
        reported_earned_credit_hours=Decimal("126"),
    )

    assert path.status == "PARTIAL"
    assert path.total_target_credits == Decimal("18")
    assert path.total_allocated_credits == Decimal("6")
    assert path.unallocated_credit_hours == Decimal("12")
    assert any("تعذر توزيع 12 ساعة" in lim for lim in path.limitations)


def test_credit_comparison_response_schema_serialization():
    from app.api.schemas.credit_timeline import CreditComparisonResponse
    from app.degree_path.credit_timeline import CreditComparison
    from dataclasses import replace

    progress_catalog, eligibility_catalog = _make_catalogs()
    timeline = simulate_credit_timeline(
        required=Decimal("132"),
        earned=Decimal("96"),
        regular_load=Decimal("18"),
        summer_enabled=False,
        summer_load=Decimal("0"),
        start_year=2026,
        start_term=AcademicTerm.FIRST_SEMESTER,
    )
    base_scenario = CreditComparisonScenario(
        scenario_id="REGULAR_18_SUMMER_0",
        mode=ComparisonMode.FASTEST,
        timeline=timeline,
        total_modeled_terms=2,
        workload_indicator="HIGH",
        preference_match=True,
    )
    course_path = allocate_strategy_degree_path(
        progress_catalog,
        eligibility_catalog,
        (),
        base_scenario,
        reported_earned_credit_hours=Decimal("96"),
    )
    scenario_with_path = replace(base_scenario, course_path=course_path)
    comparison = CreditComparison(
        policy_version="P15_6_CREDIT_COMPARISON_V1",
        scenarios=(scenario_with_path,),
        evaluated_scenarios=1,
        limitations=("None",),
    )

    response = CreditComparisonResponse.model_validate(comparison)
    data = response.model_dump()

    assert data["policy_version"] == "P15_6_CREDIT_COMPARISON_V1"
    assert len(data["scenarios"]) == 1
    sc = data["scenarios"][0]
    assert sc["course_path"] is not None
    assert sc["course_path"]["strategy"] == "FASTEST"
    assert sc["course_path"]["status"] == "COMPLETE"
    assert sc["course_path"]["total_allocated_credits"] == Decimal("36")
    assert len(sc["course_path"]["terms"]) == 2
    assert sc["course_path"]["terms"][0]["allocated_credit_hours"] == Decimal("18")
    assert sc["course_path"]["terms"][1]["allocated_credit_hours"] == Decimal("18")

