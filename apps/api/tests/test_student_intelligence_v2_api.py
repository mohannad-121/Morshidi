from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.routes.student import get_diagnostic_service, get_student_service
from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.student_intelligence.profile_v2 import StudentIntelligenceProfileV2

OWNER = "11111111-1111-1111-1111-111111111111"
SESSION = "22222222-2222-2222-2222-222222222222"
NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)


class StudentFake:
    owners: list[str] = []

    async def get_student_intelligence_v2(self, owner: str):
        self.owners.append(owner)
        return StudentIntelligenceProfileV2(
            "profile", "institution", "plan", "STUDENT_INTELLIGENCE_PROFILE_V2",
            "MORSHIDI_SKILL_TAXONOMY_V2", "EVIDENCE_FUSION_V1", NOW, "snapshot",
            None, None, Decimal("0"), 0, 0, 0, 0, 0, "NEW", "INSUFFICIENT_EVIDENCE",
            "INSUFFICIENT", "COLD_START_NO_PERFORMANCE_EVIDENCE", True, False, None, None,
            (), (), (), {}, ("Modeled only",))


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
