"""Regression coverage for Student-Intelligence-aware advisor composition."""

from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.advisor.models import AdvisorIntent
from app.advisor.provider import RawAdvisorInterpretation
from app.advisor.student_intelligence_context import (
    project_course_fit,
    project_student_intelligence,
    render_personalized_recommendations_ar,
    render_student_intelligence_ar,
)
from app.services.advisor import AdvisorService
from app.progress.engine import calculate_academic_progress
from app.progress.models import (AcademicProgressCatalog, ProgressPlanCourse,
                                 ProgressRequirementGroup, ProgressStudyPlan, RequirementType)
from app.recommendations.engine import recommend_courses
from app.rules.models import (AttemptOutcome, CanTakeCatalog, CourseCatalogStatus,
                              CourseIdentity, DependencyGroup, DependencyType,
                              PlanCourseRule, PrerequisiteLogicStatus, StudentCourseAttempt)
from app.student.models import (PerformanceProvenance, PerformanceVerificationState,
                                StudentAcademicState, StudentCourseAttemptRecord)
from app.student_intelligence.adaptive import (FAKE_UNIVERSITY_GRADE_POLICY_V1,
                                                build_adaptive_courses)
from app.student_intelligence.profile_v2 import build_student_intelligence_profile_v2
from app.university_sync.grading_policy import grading_policy_source_reference
from tests.test_advisor_service import (
    OWNER,
    FakeCatalogRepository,
    FakeProvider,
    FakeStudentRepository,
)


PROMPT_A = (
    "بناءً على سجلي الأكاديمي، شو أقوى المهارات عندي؟\n"
    "وإيش الأدلة اللي بنيت كلامك عليها؟"
)
PROMPT_B = (
    "شو المواد اللي بقدر أسجلها الفصل الجاي؟\n"
    "ومن بين المواد المسموحة أيها أنسب إلي بناءً على أدائي وعلاماتي السابقة؟"
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _profile():  # type: ignore[no-untyped-def]
    skills = (
        SimpleNamespace(skill_id="PYTHON", score=94, confidence="HIGH",
                        university_evidence_count=4, diagnostic_evidence_count=0),
        SimpleNamespace(skill_id="MACHINE_LEARNING", score=91, confidence="HIGH",
                        university_evidence_count=3, diagnostic_evidence_count=0),
        SimpleNamespace(skill_id="PROGRAMMING", score=88, confidence="MEDIUM",
                        university_evidence_count=2, diagnostic_evidence_count=0),
        SimpleNamespace(skill_id="STATISTICS", score=55, confidence="MEDIUM",
                        university_evidence_count=2, diagnostic_evidence_count=0),
    )
    return SimpleNamespace(
        skills=skills,
        strengths=("PYTHON", "MACHINE_LEARNING", "PROGRAMMING"),
        development_areas=("STATISTICS",),
        evidence_quality="AUTHORITATIVE",
        cold_start_status="ESTABLISHED_ACADEMIC_EVIDENCE",
        diagnostic_recommended=False,
        limitations=("Modeled intelligence is not an official university evaluation.",),
    )


@pytest.mark.anyio
async def test_exact_production_prompt_a_answers_skills_and_evidence_not_only_gpa() -> None:
    calls: list[str] = []

    async def load(owner: str):  # type: ignore[no-untyped-def]
        calls.append(owner)
        return _profile()

    provider = FakeProvider(RawAdvisorInterpretation("GENERAL_CHAT", general_response="wrong"))
    service = AdvisorService(FakeStudentRepository(), FakeCatalogRepository(), provider,
                             intelligence_loader=load)
    result = await service.advise_with_explanation(OWNER, PROMPT_A)

    assert result.structured_result.intent is AdvisorIntent.ACADEMIC_STATUS
    assert calls == [OWNER]
    assert provider.calls == []
    assert "بايثون" in (result.explanation or "")
    assert "تعلم الآلة" in (result.explanation or "")
    assert "أدلة جامعية" in (result.explanation or "")
    assert "المعدل التراكمي وحده" in (result.explanation or "")
    assert "معدلك التراكمي هو" not in (result.explanation or "")


@pytest.mark.anyio
async def test_english_student_intelligence_query_is_answered_in_english() -> None:
    async def load(_: str):  # type: ignore[no-untyped-def]
        return _profile()

    service = AdvisorService(FakeStudentRepository(), FakeCatalogRepository(), FakeProvider(
        RawAdvisorInterpretation("GENERAL_CHAT", general_response="wrong")),
        intelligence_loader=load)
    result = await service.advise_with_explanation(OWNER, "What are my strongest skills and what evidence supports them?")
    assert result.structured_result.intent is AdvisorIntent.ACADEMIC_STATUS
    assert "strongest modeled skills" in (result.explanation or "")
    assert "GPA alone" in (result.explanation or "")


@pytest.mark.anyio
async def test_exact_production_prompt_b_preserves_eligibility_and_adds_fit_ranking() -> None:
    students = FakeStudentRepository()
    catalogs = FakeCatalogRepository()
    baseline_service = AdvisorService(students, catalogs, FakeProvider(
        RawAdvisorInterpretation("GENERAL_CHAT", general_response="wrong")))
    baseline = await baseline_service.advise(OWNER, PROMPT_B)
    legal = tuple(item.course_code for item in baseline.authoritative_payload.ranked_recommendations)
    assert legal

    adaptive_items = []
    for rank, code in enumerate(reversed(legal), 1):
        adaptive_items.append(SimpleNamespace(
            course_code=code, rank=rank, fit_score=90 - rank,
            confidence="HIGH", eligible=True,
            personalized_difficulty=SimpleNamespace(
                level="MODERATE", contributing_skills=("PROGRAMMING", "PYTHON")),
            risk_factors=(),
        ))
    adaptive = SimpleNamespace(recommendations=tuple(adaptive_items))
    adaptive_calls: list[str] = []

    async def load_adaptive(owner: str):  # type: ignore[no-untyped-def]
        adaptive_calls.append(owner)
        return adaptive

    service = AdvisorService(FakeStudentRepository(), FakeCatalogRepository(), FakeProvider(
        RawAdvisorInterpretation("GENERAL_CHAT", general_response="wrong")),
        adaptive_loader=load_adaptive)
    response = await service.advise_with_explanation(OWNER, PROMPT_B)
    after = tuple(item.course_code for item in
                  response.structured_result.authoritative_payload.ranked_recommendations)

    assert response.structured_result.intent is AdvisorIntent.COURSE_RECOMMENDATIONS
    assert set(after) == set(legal)
    assert after == legal
    assert adaptive_calls == [OWNER]
    assert f"عندك {len(legal)} مادة مؤهلة أكاديميًا" in (response.explanation or "")
    assert "من ناحية ملاءمة قدراتك الحالية" in (response.explanation or "")
    assert "ملاءمة شخصية" in (response.explanation or "")
    assert "لا تضيف مادة غير مؤهلة" in (response.explanation or "")

    full_response = await service.advise_with_explanation(
        OWNER, PROMPT_B + "\nاعرضلي القائمة الكاملة للمواد المؤهلة.")
    assert "القائمة الكاملة للمواد المؤهلة أكاديميًا" in (
        full_response.explanation or "")
    assert all(code in (full_response.explanation or "") for code in legal)
    assert adaptive_calls == [OWNER, OWNER]


@pytest.mark.anyio
async def test_strengths_and_suitable_courses_are_composed_without_dropping_a_clause() -> None:
    baseline = await AdvisorService(
        FakeStudentRepository(), FakeCatalogRepository(), FakeProvider(
            RawAdvisorInterpretation("GENERAL_CHAT", general_response="wrong"))).advise(
                OWNER, "شو أقوى مهاراتي، وشو المواد اللي بتناسبني؟")
    legal = tuple(item.course_code for item in baseline.authoritative_payload.ranked_recommendations)
    adaptive = SimpleNamespace(recommendations=tuple(SimpleNamespace(
        course_code=code, rank=rank, fit_score=80, confidence="MEDIUM", eligible=True,
        personalized_difficulty=SimpleNamespace(
            level="MODERATE", contributing_skills=("PROGRAMMING",)), risk_factors=())
        for rank, code in enumerate(legal, 1)))

    async def load_profile(_: str):  # type: ignore[no-untyped-def]
        return _profile()

    async def load_adaptive(_: str):  # type: ignore[no-untyped-def]
        return adaptive

    service = AdvisorService(FakeStudentRepository(), FakeCatalogRepository(), FakeProvider(
        RawAdvisorInterpretation("GENERAL_CHAT", general_response="wrong")),
        intelligence_loader=load_profile, adaptive_loader=load_adaptive)
    result = await service.advise_with_explanation(
        OWNER, "شو أقوى مهاراتي، وشو المواد اللي بتناسبني؟")
    assert result.structured_result.intent is AdvisorIntent.COURSE_RECOMMENDATIONS
    assert "من أبرز نقاط قوتك" in (result.explanation or "")
    assert "مادة مؤهلة أكاديميًا" in (result.explanation or "")


def test_bounded_context_contains_only_explanation_safe_v2_fields() -> None:
    bounded = project_student_intelligence(_profile())
    payload = asdict(bounded)
    assert len(payload["skills"]) >= 3
    assert set(payload["skills"][0]) == {
        "skill_id", "label_ar", "score", "confidence", "university_evidence_count",
        "diagnostic_evidence_count", "evidence_limitation", "classification",
    }
    serialized = repr(payload).casefold()
    for forbidden in ("raw_grade", "raw_numeric_grade", "answer_key", "diagnostic_answer",
                      "weight", "grading_policy"):
        assert forbidden not in serialized


def test_course_fit_projection_rejects_any_eligible_set_change() -> None:
    deterministic = SimpleNamespace(ranked_recommendations=(
        SimpleNamespace(course_code="A"), SimpleNamespace(course_code="B")))
    adaptive = SimpleNamespace(recommendations=(
        SimpleNamespace(course_code="A", eligible=True),))
    with pytest.raises(ValueError, match="eligible set"):
        project_course_fit(adaptive, deterministic)  # type: ignore[arg-type]


def test_course_fit_is_sorted_by_fit_then_deterministic_progression_rank() -> None:
    deterministic = SimpleNamespace(ranked_recommendations=(
        SimpleNamespace(course_code="PLAN_FIRST", rank=1),
        SimpleNamespace(course_code="TIE_LATER", rank=3),
        SimpleNamespace(course_code="TIE_EARLIER", rank=2),
    ))
    adaptive = SimpleNamespace(recommendations=(
        SimpleNamespace(
            course_code="PLAN_FIRST", fit_score=70, confidence="HIGH", eligible=True,
            personalized_difficulty=SimpleNamespace(
                level="MODERATE", contributing_skills=("PROGRAMMING",)), risk_factors=()),
        SimpleNamespace(
            course_code="TIE_LATER", fit_score=90, confidence="HIGH", eligible=True,
            personalized_difficulty=SimpleNamespace(
                level="MODERATE", contributing_skills=("PROGRAMMING",)), risk_factors=()),
        SimpleNamespace(
            course_code="TIE_EARLIER", fit_score=90, confidence="HIGH", eligible=True,
            personalized_difficulty=SimpleNamespace(
                level="MODERATE", contributing_skills=("PROGRAMMING",)), risk_factors=()),
    ))

    fits = project_course_fit(adaptive, deterministic)  # type: ignore[arg-type]

    assert tuple(item.course_code for item in fits) == (
        "TIE_EARLIER", "TIE_LATER", "PLAN_FIRST")
    assert tuple(item.fit_score for item in fits) == (90, 90, 70)
    assert tuple(item.rank for item in fits) == (1, 2, 3)


def _modeled_202310001():  # type: ignore[no-untyped-def]
    fixture_dir = Path(__file__).parents[1] / "app" / "p16_sandbox" / "fixtures"
    academic = json.loads((fixture_dir / "academic-records.json").read_text(encoding="utf-8"))
    source = next(row for row in academic["records"] if row["student_id"] == "202310001")
    courses = json.loads((fixture_dir / "courses.json").read_text(encoding="utf-8"))
    plan = FAKE_UNIVERSITY_GRADE_POLICY_V1.study_plan_id
    institution = FAKE_UNIVERSITY_GRADE_POLICY_V1.institution_id
    profile_id = "modeled-202310001"
    now = datetime(2026, 10, 12, tzinfo=timezone.utc)
    current_codes = tuple(row["course_code"] for row in source["current_registered_sections"])
    attempts = tuple(StudentCourseAttempt(row["course_code"], AttemptOutcome.PASSED)
                     for row in source["attempts"]) + tuple(
                         StudentCourseAttempt(code, AttemptOutcome.IN_PROGRESS)
                         for code in current_codes)
    state = StudentAcademicState(
        profile_id, "owner-202310001", plan, Decimal(str(source["cumulative_gpa"])),
        Decimal("100"), Decimal(str(source["earned_credits"])), attempts, now, now)
    semester_dates = {"2023-1": date(2023, 9, 1), "2023-2": date(2024, 2, 1),
                      "2024-1": date(2024, 9, 1), "2024-2": date(2025, 2, 1),
                      "2025-1": date(2025, 9, 1)}
    records = tuple(StudentCourseAttemptRecord(
        f"record-{index}", profile_id, row["course_code"], AttemptOutcome.PASSED, 1,
        row["semester_name"], semester_dates[row["semester_id"]], None,
        "FAKE_UNIVERSITY_SYNC", now, now,
        raw_numeric_grade=Decimal(str(row["numeric_grade"])),
        performance_provenance=PerformanceProvenance.OFFICIAL_VERIFIED,
        performance_verification_state=PerformanceVerificationState.VERIFIED,
        performance_source_reference=grading_policy_source_reference(
            institution, "FAKE_UNIVERSITY_GRADING_POLICY_V1"),
    ) for index, row in enumerate(source["attempts"], 1))

    group_specs = {
        "متطلبات الجامعة الإجبارية": ("UNIVERSITY_REQUIRED", "university", RequirementType.REQUIRED, "18"),
        "متطلبات الجامعة الاختيارية": ("UNIVERSITY_ELECTIVE", "university", RequirementType.ELECTIVE, "9"),
        "متطلبات الكلية الإجبارية": ("FACULTY_REQUIRED", "faculty", RequirementType.REQUIRED, "21"),
        "المتطلبات المساندة": ("SUPPORTING_REQUIRED", "supporting", RequirementType.REQUIRED, "12"),
        "متطلبات التخصص الإجبارية": ("MAJOR_REQUIRED", "major", RequirementType.REQUIRED, "63"),
        "متطلبات التخصص الاختيارية": ("MAJOR_ELECTIVE", "major", RequirementType.ELECTIVE, "9"),
    }
    group_ids = {name: f"group-{index}" for index, name in enumerate(group_specs, 1)}
    groups = tuple(ProgressRequirementGroup(
        group_ids[name], plan, spec[0], name, None, spec[1], spec[2], Decimal(spec[3]), index)
        for index, (name, spec) in enumerate(group_specs.items(), 1))
    plan_courses = tuple(ProgressPlanCourse(
        f"pc-{row['code']}", plan, group_ids[row["group"]], row["code"],
        CourseCatalogStatus.KNOWN, Decimal(str(row["credits"])), index,
        row["name"], None,
    ) for index, row in enumerate(courses, 1))
    course_codes = {row["code"] for row in courses}
    referenced = {code for row in courses for code in row["prerequisites"]} - course_codes
    identities = tuple(CourseIdentity(code, CourseCatalogStatus.KNOWN)
                       for code in sorted(course_codes)) + tuple(
                           CourseIdentity(code, CourseCatalogStatus.REFERENCED_ONLY)
                           for code in sorted(referenced))
    rules = []
    for row in courses:
        prerequisites = tuple(row["prerequisites"])
        if row["review_required"]:
            status = PrerequisiteLogicStatus.SOURCE_CONFLICT
        elif prerequisites and any(code in referenced for code in prerequisites):
            status = PrerequisiteLogicStatus.UNRESOLVED
        elif prerequisites:
            status = PrerequisiteLogicStatus.VERIFIED
        else:
            status = PrerequisiteLogicStatus.NOT_APPLICABLE
        dependencies = (tuple(DependencyGroup(index, DependencyType.PREREQUISITE, (code,))
                              for index, code in enumerate(prerequisites, 1))
                        if status is PrerequisiteLogicStatus.VERIFIED else ())
        rules.append(PlanCourseRule(
            row["code"], status, dependencies,
            ",".join(prerequisites) or None, row["name"], Decimal(str(row["credits"]))))
    progress_catalog = AcademicProgressCatalog(ProgressStudyPlan(plan, Decimal("132")), groups, plan_courses)
    eligibility_catalog = CanTakeCatalog(plan, tuple(rules), identities, True)
    progress = calculate_academic_progress(
        progress_catalog, attempts, reported_cumulative_gpa=state.reported_cumulative_gpa,
        reported_gpa_scale=state.reported_gpa_scale,
        reported_earned_credit_hours=state.reported_earned_credit_hours)
    recommendations = recommend_courses(
        progress_catalog, eligibility_catalog, attempts,
        reported_cumulative_gpa=state.reported_cumulative_gpa,
        reported_gpa_scale=state.reported_gpa_scale,
        reported_earned_credit_hours=state.reported_earned_credit_hours)
    profile = build_student_intelligence_profile_v2(
        state, institution, records, FAKE_UNIVERSITY_GRADE_POLICY_V1, generated_at=now)
    adaptive = build_adaptive_courses(
        state, institution, progress_catalog, eligibility_catalog, progress,
        recommendations, records, generated_at=now,
        grade_policy=FAKE_UNIVERSITY_GRADE_POLICY_V1,
        fused_skill_scores={skill.skill_id: skill.score for skill in profile.skills
                            if skill.score is not None})
    return profile, recommendations, adaptive


def test_modeled_202310001_application_responses_use_real_fixture_evidence() -> None:
    profile, recommendations, adaptive = _modeled_202310001()
    assert profile.verified_grade_count == 32
    assert profile.cumulative_gpa == Decimal("93.6")
    assert profile.earned_credits == Decimal("96")
    answer_a = render_student_intelligence_ar(project_student_intelligence(profile))
    fits = project_course_fit(adaptive, recommendations)
    answer_b = render_personalized_recommendations_ar(recommendations, fits)
    assert "بايثون" in answer_a and "أدلة جامعية" in answer_a
    legal = {item.course_code for item in recommendations.ranked_recommendations}
    assert legal == {item.course_code for item in adaptive.recommendations}
    assert len(legal) == 29
    assert {item.course_code for item in fits[:5]} <= legal
    assert tuple(item.fit_score for item in fits[:5]) == tuple(sorted(
        (item.fit_score for item in fits[:5]), reverse=True))
    tied_scores = {}
    for item in fits:
        tied_scores.setdefault(item.fit_score, []).append(item.progression_rank)
    assert all(ranks == sorted(ranks) for ranks in tied_scores.values())
    assert "عندك 29 مادة مؤهلة أكاديميًا" in answer_b
    assert "من ناحية ملاءمة قدراتك الحالية" in answer_b
    assert "من ناحية أولوية التقدم في الخطة" in answer_b
    assert "وهذا ترتيب مختلف عن الملاءمة الشخصية" in answer_b
    assert "يجمع أولوية التقدم الأكاديمي مع الملاءمة" not in answer_b
    assert tuple(item.course_code for item in fits[:5]) == (
        "1509999", "0200115", "0200154", "0300155", "1505367")
    shown_codes = {code for code in legal if code in answer_b}
    assert len(shown_codes) < len(legal)
    assert "القائمة الكاملة للمواد المؤهلة أكاديميًا:" not in answer_b

    full_answer = render_personalized_recommendations_ar(
        recommendations, fits, include_full_eligible_list=True)
    assert "القائمة الكاملة للمواد المؤهلة أكاديميًا" in full_answer
    assert all(code in full_answer for code in legal)
