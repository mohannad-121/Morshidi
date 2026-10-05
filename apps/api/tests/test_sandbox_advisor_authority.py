"""Sandbox/real academic-authority separation for authenticated student chat."""

from __future__ import annotations

import asyncio
from dataclasses import replace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.advisor.explanation import deterministic_explanation
from app.advisor.models import (
    AdvisorIntent,
    AnswerAuthority,
    CourseResolution,
    EntityResolutionStatus,
    NormalizedAdvisorRequest,
    ResolvedCourseReference,
)
from app.advisor.orchestrator import AdvisorContext, orchestrate_advisor_request
from app.advisor.provider import RawAdvisorInterpretation
from app.p16_sandbox.academic_catalog import (
    SANDBOX_PREREQUISITE_SEMANTICS,
    SANDBOX_RULE_AUTHORITY,
    SANDBOX_RULE_VERSION,
    SandboxAcademicCatalogRepository,
)
from app.p16_sandbox.advisor_source import SandboxAdvisorStudentSource
from app.p16_sandbox.sis_adapter import SandboxSISAdapter
from app.p16_sandbox.tenant import SANDBOX_INSTITUTION_ID
from app.rules.models import (
    CanTakeCatalog,
    CanTakeDecision,
    CourseCatalogStatus,
    CourseIdentity,
    Decision,
    PlanCourseRule,
    PrerequisiteLogicStatus,
    StudentCourseAttempt,
    AttemptOutcome,
)
from app.services.advisor import AdvisorService
from app.api.routes.advisor import router as advisor_router
from app.core.config import settings


TARGET = ResolvedCourseReference("1505311", "تعلم الالة")
FORBIDDEN_STUDENT_ENUMS = (
    "PREREQUISITE_LOGIC_UNRESOLVED",
    "SOURCE_CONFLICT",
    "REVIEW_REQUIRED",
    "INSUFFICIENT_CONTEXT",
)


async def _sandbox_result(attempt_codes: tuple[str, ...]):
    repository = SandboxAcademicCatalogRepository()
    catalog = await repository.load_plan_eligibility_catalog("12")
    request = NormalizedAdvisorRequest(
        "هل بقدر انزل 1505311؟",
        AdvisorIntent.COURSE_ELIGIBILITY,
        course_resolution=CourseResolution(
            EntityResolutionStatus.RESOLVED, resolved_course=TARGET,
        ),
    )
    attempts = tuple(StudentCourseAttempt(code, AttemptOutcome.PASSED) for code in attempt_codes)
    result = orchestrate_advisor_request(
        request, AdvisorContext(eligibility_catalog=catalog, student_attempts=attempts),
    )
    return replace(
        result,
        presentation_course_catalog=await repository.load_advisor_course_catalog("12"),
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("completed", "decision", "shown", "hidden"),
    (
        ((), Decision.NOT_ELIGIBLE,
         ("البرمجة بلغة بايثون", "مقدمة في الذكاء الاصطناعي"), ()),
        (("1505101",), Decision.NOT_ELIGIBLE,
         ("مقدمة في الذكاء الاصطناعي",), ("البرمجة بلغة بايثون",)),
        (("1505201",), Decision.NOT_ELIGIBLE,
         ("البرمجة بلغة بايثون",), ("مقدمة في الذكاء الاصطناعي",)),
        (("1505101", "1505201"), Decision.ELIGIBLE, (), ()),
    ),
)
async def test_sandbox_1505311_all_of_matrix(completed, decision, shown, hidden) -> None:
    result = await _sandbox_result(completed)
    payload = result.authoritative_payload
    assert isinstance(payload, CanTakeDecision)
    assert payload.decision is decision
    explanation = deterministic_explanation("هل بقدر انزل 1505311؟", result)
    assert explanation is not None
    for value in shown:
        assert value in explanation.text
    for value in hidden:
        assert value not in explanation.text
    assert not any(value in explanation.text for value in FORBIDDEN_STUDENT_ENUMS)


@pytest.mark.anyio
async def test_sandbox_catalog_is_explicit_global_all_of_policy() -> None:
    catalog = await SandboxAcademicCatalogRepository().load_plan_eligibility_catalog("12")
    rules = {rule.course_code: rule for rule in catalog.plan_courses}
    target = rules["1505311"]
    assert SANDBOX_PREREQUISITE_SEMANTICS == "ALL_OF"
    assert SANDBOX_RULE_AUTHORITY == "SYNTHETIC_SANDBOX_ACADEMIC_POLICY"
    assert SANDBOX_RULE_VERSION == "2026.10.05.v1"
    assert target.prerequisite_logic_status is PrerequisiteLogicStatus.VERIFIED
    assert tuple(group.option_course_codes for group in target.dependency_groups) == (
        ("1505101",), ("1505201",),
    )
    assert target.raw_prerequisite_text == "1505101,1505201"


@pytest.mark.anyio
async def test_other_nonverified_real_courses_do_not_leak_into_sandbox_policy() -> None:
    catalog = await SandboxAcademicCatalogRepository().load_plan_eligibility_catalog("12")
    rules = {rule.course_code: rule for rule in catalog.plan_courses}
    assert rules["1505320"].prerequisite_logic_status is PrerequisiteLogicStatus.UNRESOLVED
    assert rules["1505366"].prerequisite_logic_status is PrerequisiteLogicStatus.UNRESOLVED
    assert rules["1505461"].prerequisite_logic_status is PrerequisiteLogicStatus.VERIFIED
    assert tuple(group.option_course_codes for group in rules["1505461"].dependency_groups) == (
        ("1505366",), ("1505415",),
    )


def test_real_source_1505311_remains_unresolved_without_guessed_semantics() -> None:
    real = CanTakeCatalog(
        "real-plan-12",
        (PlanCourseRule(
            "1505311", PrerequisiteLogicStatus.UNRESOLVED,
            raw_prerequisite_text="1505101,1505201", target_name_ar="تعلم الالة",
        ),),
        (CourseIdentity("1505311", CourseCatalogStatus.KNOWN),),
    )
    request = NormalizedAdvisorRequest(
        "هل بقدر انزل 1505311؟", AdvisorIntent.COURSE_ELIGIBILITY,
        course_resolution=CourseResolution(EntityResolutionStatus.RESOLVED, resolved_course=TARGET),
    )
    result = orchestrate_advisor_request(request, AdvisorContext(eligibility_catalog=real))
    payload = result.authoritative_payload
    assert result.authority is AnswerAuthority.REVIEW_REQUIRED
    assert isinstance(payload, CanTakeDecision)
    assert payload.raw_prerequisite_text == "1505101,1505201"
    explanation = deterministic_explanation(request.user_message, result)
    assert explanation is not None
    assert "طريقة تطبيقها غير مؤكدة" in explanation.text
    assert not any(value in explanation.text for value in FORBIDDEN_STUDENT_ENUMS)


class _Provider:
    def interpret(self, request):  # type: ignore[no-untyped-def]
        return RawAdvisorInterpretation(
            AdvisorIntent.COURSE_ELIGIBILITY.value,
            course_codes_mentioned=("1505311",),
        )


class _ForbiddenRealRepository:
    async def load_student_academic_state(self, owner):  # type: ignore[no-untyped-def]
        raise AssertionError("sandbox request reached the real student repository")


class _ForbiddenRealCatalog:
    async def load_advisor_course_catalog(self, plan):  # type: ignore[no-untyped-def]
        raise AssertionError("sandbox request reached the real catalog")

    async def load_plan_eligibility_catalog(self, plan):  # type: ignore[no-untyped-def]
        raise AssertionError("sandbox request reached the real catalog")


@pytest.mark.anyio
async def test_authenticated_sandbox_context_uses_actual_persona_and_synthetic_catalog() -> None:
    adapter = SandboxSISAdapter()
    catalog = SandboxAcademicCatalogRepository()
    service = AdvisorService(
        _ForbiddenRealRepository(), _ForbiddenRealCatalog(), _Provider(),
        sandbox_student_source=SandboxAdvisorStudentSource(adapter),
        sandbox_catalog_repository=catalog,
    )
    response = await service.advise_with_explanation(
        "11111111-1111-1111-1111-111111111111",
        "هل بقدر انزل 1505311؟",
        institution_id=SANDBOX_INSTITUTION_ID,
        sandbox_persona_id="202410002",
    )
    payload = response.structured_result.authoritative_payload
    assert isinstance(payload, CanTakeDecision)
    assert payload.study_plan_id == "12"
    assert payload.decision is Decision.NOT_ELIGIBLE
    assert payload.prerequisite_logic_status is PrerequisiteLogicStatus.VERIFIED
    assert response.explanation == (
        "لا يمكنك تسجيل تعلم الالة حاليًا لأنك لم تُكمل: "
        "مقدمة في الذكاء الاصطناعي (1505201)."
    )
    assert not any(value in response.explanation for value in FORBIDDEN_STUDENT_ENUMS)


def test_verified_auth_to_http_advisor_response_is_sandbox_governed(monkeypatch) -> None:
    def auth_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/v1/user"
        return httpx.Response(200, json={
            "id": "11111111-1111-1111-1111-111111111111",
            "app_metadata": {
                "institution_id": SANDBOX_INSTITUTION_ID,
                "sandbox_persona_id": "202410002",
            },
        })

    monkeypatch.setattr(settings, "supabase_url", "https://auth.example")
    monkeypatch.setattr(settings, "supabase_secret_key", SecretStr("server-secret"))
    application = FastAPI()
    application.state.auth_http_client = httpx.AsyncClient(
        transport=httpx.MockTransport(auth_handler)
    )
    application.state.advisor_service = AdvisorService(
        _ForbiddenRealRepository(), _ForbiddenRealCatalog(), _Provider(),
        sandbox_student_source=SandboxAdvisorStudentSource(SandboxSISAdapter()),
        sandbox_catalog_repository=SandboxAcademicCatalogRepository(),
    )
    application.include_router(advisor_router)
    try:
        with TestClient(application) as client:
            response = client.post(
                "/api/v1/me/advisor",
                headers={"Authorization": "Bearer private-token"},
                json={"message": "هل بقدر انزل 1505311؟"},
            )
    finally:
        asyncio.run(application.state.auth_http_client.aclose())

    assert response.status_code == 200
    body = response.json()
    assert body["answer_authority"] == "DETERMINISTIC"
    assert body["result"]["decision"] == "NOT_ELIGIBLE"
    assert body["result"]["prerequisite_logic_status"] == "verified"
    assert body["explanation"] == (
        "لا يمكنك تسجيل تعلم الالة حاليًا لأنك لم تُكمل: "
        "مقدمة في الذكاء الاصطناعي (1505201)."
    )
    assert "private-token" not in response.text
    assert not any(value in body["explanation"] for value in FORBIDDEN_STUDENT_ENUMS)
