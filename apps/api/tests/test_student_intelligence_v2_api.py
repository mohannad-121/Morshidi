from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.routes.student import get_diagnostic_service, get_student_service
from app.api.schemas.student_intelligence_v2 import DiagnosticSessionResponse
from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.student_intelligence.diagnostic_service import DiagnosticConflict
from app.student_intelligence.profile_v2 import SkillDimensionV2, StudentIntelligenceProfileV2

OWNER = "11111111-1111-1111-1111-111111111111"
SESSION = "22222222-2222-2222-2222-222222222222"
NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)


def _internal_profile() -> StudentIntelligenceProfileV2:
    skill = SkillDimensionV2(
        skill_id="PROGRAMMING", score=82, confidence="HIGH", evidence_quality="MODELED",
        university_evidence_count=0, diagnostic_evidence_count=6,
        contributing_courses=(), contributing_question_domains=("PROGRAMMING_REASONING",),
        source_types=("COMPLETED_QUICK_DIAGNOSTIC",), reason_codes=("DIAGNOSTIC_ONLY",),
        reasoning_patterns=("CONSISTENT_REASONING",),
    )
    return StudentIntelligenceProfileV2(
        student_id="profile", institution_id="institution", study_plan_id="plan",
        intelligence_model_version="STUDENT_INTELLIGENCE_PROFILE_V2",
        taxonomy_version="MORSHIDI_SKILL_TAXONOMY_V2",
        fusion_policy_version="EVIDENCE_FUSION_V1", generated_at=NOW,
        source_snapshot_version="snapshot", cumulative_gpa=None, gpa_scale=None,
        earned_credits=Decimal("0"), verified_grade_count=0, completed_course_count=0,
        failed_course_count=0, repeated_course_count=0, current_course_count=0,
        academic_progress_band="NEW", performance_trend="INSUFFICIENT_EVIDENCE",
        evidence_quality="INSUFFICIENT", cold_start_status="COLD_START_NO_PERFORMANCE_EVIDENCE",
        diagnostic_recommended=False, diagnostic_completed=True,
        latest_assessment_version="QUICK_DIAGNOSTIC_V2", latest_completed_at=NOW,
        skills=(skill,), strengths=("PROGRAMMING",), development_areas=(), preferences={},
        limitations=("Modeled only",),
    )


class StudentFake:
    owners: list[str] = []

    async def get_student_intelligence_v2(self, owner: str):
        self.owners.append(owner)
        return _internal_profile()


class DiagnosticFake:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    async def status(self, owner, assessment_version="QUICK_DIAGNOSTIC_V1"):
        self.calls.append(("status", owner, assessment_version))
        return {"onboarding_status": "NOT_STARTED", "diagnostic_completed": False,
                "active_session_id": None, "latest_assessment_version": None,
                "latest_completed_at": None}

    async def start(self, owner, assessment_version="QUICK_DIAGNOSTIC_V1"):
        self.calls.append(("start", owner, assessment_version))
        return _session()

    async def next_question(self, owner, session_id):
        self.calls.append(("next", owner, session_id)); return _session()

    async def answer(self, owner, session_id, question_id, selected_option,
                     response_time_ms, self_confidence):
        self.calls.append(("answer", owner, session_id, question_id, selected_option,
                           response_time_ms, self_confidence)); return _session()

    async def abandon(self, owner, session_id):
        self.calls.append(("abandon", owner, session_id))


class CompletingDiagnosticFake(DiagnosticFake):
    def __init__(self) -> None:
        super().__init__()
        self.completed = False

    async def answer(self, owner, session_id, question_id, selected_option,
                     response_time_ms, self_confidence):
        self.calls.append(("answer", owner, session_id, question_id, selected_option,
                           response_time_ms, self_confidence))
        if self.completed:
            raise DiagnosticConflict("Question is not currently issued")
        self.completed = True
        result_domains = (
            "PROGRAMMING_REASONING",
            "LOGICAL_PROBLEM_SOLVING",
            "QUANTITATIVE_MATH",
            "STATISTICS_DATA_REASONING",
            "THEORY_CONCEPTUAL_UNDERSTANDING",
        )
        return {
            "session_id": SESSION, "status": "COMPLETED",
            "assessment_version": "QUICK_DIAGNOSTIC_V2", "answered_count": 30,
            "maximum_questions": 30, "question": None,
            "results": [
                {"domain": domain, "score": 82, "confidence": "HIGH",
                 "response_count": 6,
                 "reasoning_patterns": ["CONSISTENT_REASONING"]}
                for domain in result_domains
            ],
            "intelligence_profile": _internal_profile(),
        }


def _session():
    return {"session_id": SESSION, "status": "IN_PROGRESS", "assessment_version": "QUICK_DIAGNOSTIC_V2",
            "answered_count": 0, "maximum_questions": 30, "question": {
                "question_id": "P01", "assessment_version": "QUICK_DIAGNOSTIC_V2",
                "prompt_ar": "سؤال", "prompt_en": "Question",
                "options": [{"option_id": "A", "text_ar": "أ", "text_en": "A"}]}}


def test_v2_profile_is_owner_derived_and_private() -> None:
    students = StudentFake()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER)
    app.dependency_overrides[get_student_service] = lambda: students
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/me/student-intelligence")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "private, no-store"
        assert students.owners == [OWNER]
        assert response.json()["skills"][0]["skill_id"] == "PROGRAMMING"
    finally:
        app.dependency_overrides.clear()


def test_diagnostic_session_schema_accepts_internal_profile_and_nested_skill_dataclasses() -> None:
    response = DiagnosticSessionResponse.model_validate({
        "session_id": SESSION, "status": "COMPLETED",
        "assessment_version": "QUICK_DIAGNOSTIC_V2", "answered_count": 30,
        "maximum_questions": 30, "question": None, "results": [],
        "intelligence_profile": _internal_profile(),
    })
    assert response.intelligence_profile is not None
    assert response.intelligence_profile.student_id == "profile"
    assert response.intelligence_profile.skills[0].skill_id == "PROGRAMMING"
    assert response.intelligence_profile.skills[0].reasoning_patterns == ["CONSISTENT_REASONING"]


def test_final_v2_answer_serializes_completed_profile_and_retry_remains_conflict() -> None:
    diagnostics = CompletingDiagnosticFake()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER)
    app.dependency_overrides[get_diagnostic_service] = lambda: diagnostics
    answer = {"question_id": "P30", "selected_option": "A",
              "response_time_ms": 12000, "self_confidence": "MEDIUM"}
    try:
        with TestClient(app) as client:
            completed = client.post(f"/api/v1/me/diagnostic/{SESSION}/answer", json=answer)
            retry = client.post(f"/api/v1/me/diagnostic/{SESSION}/answer", json=answer)
        assert completed.status_code == 200
        body = completed.json()
        assert body["status"] == "COMPLETED"
        assert body["answered_count"] == 30
        assert body.get("question") is None
        assert len(body["results"]) == 5
        assert body["intelligence_profile"]
        assert body["intelligence_profile"]["skills"][0]["skill_id"] == "PROGRAMMING"
        serialized = str(body).lower()
        assert all(hidden not in serialized for hidden in (
            "raw diagnostic answers", "raw_diagnostic_answers", "answer_key", "answer_keys",
            "correct_option", "distractor reasoning", "distractor_reasoning",
            "scoring_weight", "scoring_weights", "difficulty_weight", "grading_formula",
            "internal_grading_formula",
        ))
        assert retry.status_code == 409
        assert len(diagnostics.calls) == 2
    finally:
        app.dependency_overrides.clear()


def test_diagnostic_answer_accepts_only_bounded_student_evidence_from_browser() -> None:
    diagnostics = DiagnosticFake()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER)
    app.dependency_overrides[get_diagnostic_service] = lambda: diagnostics
    try:
        with TestClient(app) as client:
            rejected = client.post(f"/api/v1/me/diagnostic/{SESSION}/answer", json={
                "question_id": "P01", "selected_option": "A", "score": 100,
                "domain": "PROGRAMMING_REASONING", "response_time_ms": 12000,
                "self_confidence": "MEDIUM"})
            accepted = client.post(f"/api/v1/me/diagnostic/{SESSION}/answer", json={
                "question_id": "P01", "selected_option": "A",
                "response_time_ms": 12000, "self_confidence": "MEDIUM"})
            legacy_shape = client.post(f"/api/v1/me/diagnostic/{SESSION}/answer", json={
                "question_id": "P01", "selected_option": "A"})
        assert rejected.status_code == 422
        assert accepted.status_code == 200
        assert legacy_shape.status_code == 200
        assert diagnostics.calls == [
            ("answer", OWNER, SESSION, "P01", "A", 12000, "MEDIUM"),
            ("answer", OWNER, SESSION, "P01", "A", None, None),
        ]
        body = accepted.json()
        assert "correct_option" not in str(body)
        assert "difficulty" not in str(body)
        assert "domain" not in str(body)
    finally:
        app.dependency_overrides.clear()


def test_unversioned_clients_default_to_v1_and_new_clients_explicitly_request_v2() -> None:
    diagnostics = DiagnosticFake()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER)
    app.dependency_overrides[get_diagnostic_service] = lambda: diagnostics
    try:
        with TestClient(app) as client:
            legacy = client.post("/api/v1/me/diagnostic/start")
            current = client.post(
                "/api/v1/me/diagnostic/start?assessment_version=QUICK_DIAGNOSTIC_V2")
        assert legacy.status_code == 200 and current.status_code == 200
        assert diagnostics.calls == [
            ("start", OWNER, "QUICK_DIAGNOSTIC_V1"),
            ("start", OWNER, "QUICK_DIAGNOSTIC_V2"),
        ]
    finally:
        app.dependency_overrides.clear()
