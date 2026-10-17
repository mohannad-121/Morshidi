from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from app.planner.learning_profile import resolve_learning_profile
from app.rules.models import AttemptOutcome, StudentCourseAttempt
from app.rules.project_credits import PLAN12_ID, is_plan12_project
from app.student.models import StudentAcademicState
from app.student_intelligence.adaptive import (
    FAKE_UNIVERSITY_INSTITUTION_GRADING_POLICY_V1,
    GradePolicyRegistry,
)
from app.student_intelligence.curriculum_mapping import (
    DEFAULT_CURRICULUM_SKILL_MAPPINGS,
    UnsupportedCurriculumIntelligenceError,
)
from app.student_intelligence.profile_v2 import build_student_intelligence_profile_v2
from app.university_sync.errors import (
    UniversityPlanAmbiguousError,
    UniversityPlanNotMappedError,
    UniversityProtocolError,
)
from app.university_sync.models import UniversityAcademicPlan, UniversityStudentProfile
from app.university_sync.service import UniversitySyncService


UNIVERSITY_ID = "10000000-0000-0000-0000-000000000001"
AI_ID = PLAN12_ID
SE_ID = "20000000-0000-0000-0000-000000000005"
NURS_ID = "30000000-0000-0000-0000-000000000005"
LAW_ID = "40000000-0000-0000-0000-000000000005"


def _row(plan_id: str, faculty_code: str, major_code: str, faculty: str, major: str) -> dict:
    return {
        "id": plan_id,
        "plan_number": "12",
        "majors": {
            "code": major_code,
            "name_ar": major,
            "name_en": major,
            "faculties": {
                "code": faculty_code,
                "name_ar": faculty,
                "name_en": faculty,
                "university_id": UNIVERSITY_ID,
            },
        },
    }


ROWS = (
    _row(AI_ID, "IT", "AI", "Faculty of Information Technology", "Artificial Intelligence"),
    _row(SE_ID, "IT", "SE", "Faculty of Information Technology", "Software Engineering"),
    _row(NURS_ID, "NURS", "NURS", "Faculty of Nursing", "Nursing"),
    _row(LAW_ID, "LAW", "LAW", "Faculty of Law", "Law"),
)


def _service(rows=ROWS) -> UniversitySyncService:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/rest/v1/study_plans"
        assert request.url.params["plan_number"] == "eq.12"
        return httpx.Response(200, json=list(rows))

    return UniversitySyncService(
        contract_client=object(),  # type: ignore[arg-type]
        supabase_url="https://local.invalid",
        service_key="local-only",
        internal_auth_secret="local-only-secret",
        university_id=UNIVERSITY_ID,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )


@pytest.mark.anyio
@pytest.mark.parametrize(("plan_key", "faculty_code", "major_code", "expected"), (
    ("ZU:IT:AI:P12", "IT", "AI", AI_ID),
    ("ZU:IT:SE:P12", "IT", "SE", SE_ID),
    ("ZU:NURS:NURS:P12", "NURS", "NURS", NURS_ID),
    ("ZU:LAW:LAW:P12", "LAW", "LAW", LAW_ID),
))
async def test_same_plan_number_resolves_only_exact_faculty_major_identity(
    plan_key: str, faculty_code: str, major_code: str, expected: str,
) -> None:
    service = _service()
    try:
        profile = UniversityStudentProfile(
            studentId="202620001", facultyCode=faculty_code, majorCode=major_code,
            planKey=plan_key, planNumber="12",
        )
        plan = UniversityAcademicPlan(
            planId="12", planKey=plan_key, planNumber="12",
            facultyCode=faculty_code, majorCode=major_code,
        )
        assert await service._resolve_study_plan(profile, plan) == expected
    finally:
        await service.close()


@pytest.mark.anyio
async def test_nursing_and_software_engineering_contract_fixtures_never_map_to_ai() -> None:
    for key, faculty, major, expected in (
        ("ZU:NURS:NURS:P12", "NURS", "NURS", NURS_ID),
        ("ZU:IT:SE:P12", "IT", "SE", SE_ID),
    ):
        service = _service()
        try:
            resolved = await service._resolve_study_plan(
                UniversityStudentProfile(
                    studentId="202620001", planKey=key, planNumber="12",
                    facultyCode=faculty, majorCode=major,
                ),
                UniversityAcademicPlan(
                    planId="12", planKey=key, planNumber="12",
                    facultyCode=faculty, majorCode=major,
                ),
            )
            assert resolved == expected
            assert resolved != AI_ID
        finally:
            await service.close()


@pytest.mark.anyio
async def test_unknown_ambiguous_and_malformed_plan_identities_fail_closed() -> None:
    service = _service()
    try:
        with pytest.raises(UniversityPlanNotMappedError):
            await service._resolve_study_plan(
                UniversityStudentProfile(studentId="202620001", planKey="ZU:IT:UNKNOWN:P12"),
                UniversityAcademicPlan(planId="12", planKey="ZU:IT:UNKNOWN:P12"),
            )
        with pytest.raises(UniversityProtocolError):
            await service._resolve_study_plan(
                UniversityStudentProfile(studentId="202620001", planKey="malformed"),
                UniversityAcademicPlan(planId="12", planKey="malformed"),
            )
    finally:
        await service.close()

    duplicate = ROWS + (_row(str(uuid4()), "IT", "SE", "Faculty of Information Technology", "Software Engineering"),)
    service = _service(duplicate)
    try:
        with pytest.raises(UniversityPlanAmbiguousError):
            await service._resolve_study_plan(
                UniversityStudentProfile(studentId="202620001", planKey="ZU:IT:SE:P12"),
                UniversityAcademicPlan(planId="12", planKey="ZU:IT:SE:P12"),
            )
    finally:
        await service.close()


def test_ai_skill_and_project_policies_do_not_leak_to_other_curricula() -> None:
    unsupported_plan = NURS_ID
    assert DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(PLAN12_ID) is not None
    assert is_plan12_project(PLAN12_ID, "1505467") is True
    assert is_plan12_project(PLAN12_ID, "1505468") is True
    for unsupported_plan_id in (SE_ID, NURS_ID, LAW_ID):
        assert DEFAULT_CURRICULUM_SKILL_MAPPINGS.resolve(unsupported_plan_id) is None
        assert resolve_learning_profile("1505467", plan_id=unsupported_plan_id).primary_type == "UNKNOWN"
        assert is_plan12_project(unsupported_plan_id, "1505467") is False
        assert is_plan12_project(unsupported_plan_id, "1505468") is False

    now = datetime(2026, 10, 17, tzinfo=timezone.utc)
    state = StudentAcademicState(
        "profile", "owner", unsupported_plan, Decimal("90"), Decimal("100"), Decimal("30"),
        (StudentCourseAttempt("1505467", AttemptOutcome.PASSED),), now, now,
    )
    with pytest.raises(UnsupportedCurriculumIntelligenceError):
        build_student_intelligence_profile_v2(
            state, UNIVERSITY_ID, (), FAKE_UNIVERSITY_INSTITUTION_GRADING_POLICY_V1,
            generated_at=now,
        )


def test_fake_university_grade_policy_is_institution_scoped_without_weakening_provenance() -> None:
    registry = GradePolicyRegistry((FAKE_UNIVERSITY_INSTITUTION_GRADING_POLICY_V1,))
    assert registry.resolve(UNIVERSITY_ID, AI_ID) is FAKE_UNIVERSITY_INSTITUTION_GRADING_POLICY_V1
    assert registry.resolve(UNIVERSITY_ID, NURS_ID) is FAKE_UNIVERSITY_INSTITUTION_GRADING_POLICY_V1
    assert registry.resolve(str(uuid4()), NURS_ID) is None

