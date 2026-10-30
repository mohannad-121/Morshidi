"""Comprehensive unit and protocol tests for Morshidi Realtime Live Voice."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import time
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
import httpx
import pytest

from app.advisor.models import AdvisorIntent, StructuredAdvisorResult
from app.api.routes.voice import get_voice_service
from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.voice.instructions import build_voice_system_instructions
from app.voice.service import VoiceService
from app.voice.session_manager import VoiceQuotaExceededError, VoiceRateLimitError, VoiceSessionManager


OWNER_A = "11111111-1111-1111-1111-111111111111"
INST_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
SECRET_KEY = "sk-fake-openai-super-secret-key-that-must-never-leak"
EPHEMERAL_KEY = "ek_realtime_ephemeral_test_token_12345"


class FakeStudentService:
    async def get_profile(self, owner_id: str):
        return SimpleNamespace(
            profile_id=owner_id,
            university_name_ar="الجامعة الهاشمية",
            university_name_en="Hashemite University",
        )

    async def resolve_student_university_id(self, owner_id: str):
        return INST_A


class FakeAdvisorToolExecutor:
    def __init__(self, owner_user_id: str):
        self.owner_user_id = owner_user_id
        self.executed_calls: list[tuple[str, str]] = []

    async def execute(self, name: str, raw_arguments: str):
        self.executed_calls.append((name, raw_arguments))
        if name == "get_remaining_requirements":
            return SimpleNamespace(
                output={
                    "ok": True,
                    "remaining_credit_hours": 12,
                    "requirements_left": ["خوارزميات متقدمة", "مشروع التخرج 2"],
                }
            )
        if name == "get_course_eligibility":
            return SimpleNamespace(
                output={
                    "ok": True,
                    "eligible": True,
                    "course_code": "CS401",
                    "reason": "جميع المتطلبات السابقة مستوفاة بنجاح",
                }
            )
        if name == "search_university_policies":
            return SimpleNamespace(
                output={
                    "ok": True,
                    "question": "شروط مرتبة الشرف",
                    "answer": "تمنح مرتبة الشرف عند التخرج بمعدل لا يقل عن 3.65 دون أي إنذار أكاديمي.",
                    "has_answer": True,
                    "evidence": [{"source": "دليل اللوائح الجامعية", "version": "2026.1"}],
                }
            )
        if name == "switch_dialect":
            return SimpleNamespace(
                output={
                    "ok": True,
                    "dialect": json.loads(raw_arguments).get("dialect", "jordanian"),
                    "message": "Switched successfully",
                }
            )
        return SimpleNamespace(output={"ok": False, "error": "UNKNOWN_TOOL"})


class FakeAdvisorService:
    def __init__(self):
        self.last_executor = None

    def build_tool_executor(self, owner_user_id: str, *, university_id: str | None = None, policy_answer_service: Any = None):
        self.last_executor = FakeAdvisorToolExecutor(owner_user_id)
        return self.last_executor


class FakeConversationStore:
    def __init__(self):
        self.messages: list[dict[str, Any]] = []
        self.preferences: dict[str, str] = {}
        self.threads: dict[str, dict[str, Any]] = {
            "test-thread-id": {
                "id": "test-thread-id",
                "title": "محادثة سابقة عن التسجيل",
                "summary_text": "الطالب مهتم بالتخرج المبكر",
            }
        }

    async def get_thread(self, owner, inst, thread_id):
        return self.threads.get(thread_id, {"id": thread_id, "title": "محادثة"})

    async def active_preferences(self, owner, inst):
        return dict(self.preferences)

    async def recent_thread_messages(self, owner, inst, thread_id, limit=10):
        return [{"role": "USER", "content": "كم باقيلي ساعات؟"}]

    async def active_memories(self, owner, inst):
        return []

    async def append_message(self, owner, inst, thread_id, role, content, provenance, message_id=None):
        row = {
            "id": message_id or str(uuid4()),
            "owner": owner,
            "role": role,
            "content": content,
            "provenance": provenance,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.messages.append(row)
        return row

    async def save_preference(self, owner, inst, key, value, msg_id):
        self.preferences[key] = value


def _build_test_voice_service(
    *,
    api_key: str | None = SECRET_KEY,
    enabled: bool = True,
    transport_handler=None,
    max_daily: int = 5,
    allowed_user_ids: str = "",
    app_env: str = "development",
) -> tuple[VoiceService, FakeAdvisorService, FakeConversationStore]:
    async def default_handler(request: httpx.Request) -> httpx.Response:
        auth_header = request.headers.get("Authorization", "")
        assert SECRET_KEY in auth_header
        if request.url.path == "/v1/live/sessions":
            return httpx.Response(
                200,
                json={
                    "id": "sess_live_test_123",
                    "object": "live.session",
                    "model": "gpt-live-1",
                    "transport": {
                        "type": "webrtc",
                        "sdp": "v=0\r\no=OpenAI ...",
                    },
                },
            )
        if request.url.path == "/v1/realtime/sessions":
            return httpx.Response(
                200,
                json={
                    "id": "sess_realtime_test_123",
                    "object": "realtime.session",
                    "model": "gpt-realtime-2.1",
                    "client_secret": {
                        "value": EPHEMERAL_KEY,
                        "expires_at": int(datetime.now(timezone.utc).timestamp()) + 60,
                    },
                },
            )
        return httpx.Response(404)

    handler = transport_handler or default_handler
    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    advisor_svc = FakeAdvisorService()
    student_svc = FakeStudentService()
    store = FakeConversationStore()
    manager = VoiceSessionManager(
        db_path=":memory:",
        max_daily_sessions_per_student=max_daily,
        min_seconds_between_starts=0.01,
    )

    voice_svc = VoiceService(
        http_client=http_client,
        advisor_service=advisor_svc,
        student_service=student_svc,
        session_manager=manager,
        conversation_store=store,
        api_key=api_key,
        enabled=enabled,
        allowed_user_ids=allowed_user_ids,
        app_env=app_env,
    )
    return voice_svc, advisor_svc, store


# ══════════════════════════════════════════════════════════════════════════
# Unit & Protocol Tests
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_session_creation_returns_sdp_answer_and_never_exposes_master_key():
    voice_svc, _, _ = _build_test_voice_service()
    session = await voice_svc.create_realtime_session(OWNER_A, sdp_offer="v=0\r\no=Browser ...")

    assert session["sdp_answer"] == "v=0\r\no=OpenAI ..."
    assert session["session_id"] == "sess_live_test_123"
    assert session["endpoint_type"] == "live"
    assert session["default_language"] == "ar"
    assert session["default_dialect"] == "msa"
    assert "get_remaining_requirements" in session["tools"]
    assert "switch_dialect" in session["tools"]

    # Security verification: Ensure the master API key NEVER leaks in returned payload
    encoded_session = json.dumps(session)
    assert SECRET_KEY not in encoded_session


@pytest.mark.anyio
async def test_voice_system_instructions_default_to_msa_and_support_jordanian_triggers():
    instructions = build_voice_system_instructions(
        university_name_ar="جامعة الزرقاء",
        active_dialect="msa",
    )

    # Invariants verification
    assert "اللغة العربية الفصحى" in instructions
    assert "احكي أردني" in instructions
    assert "احكي معي باللهجة الأردنية" in instructions
    assert "من هسا رح أحكي معك باللهجة الأردنية" in instructions
    assert "ارجع احكي فصحى" in instructions
    assert "الذكاء الاصطناعي يشرح — القواعد الحتمية تقرر" in instructions
    assert "جامعة الزرقاء" in instructions


@pytest.mark.anyio
async def test_voice_disabled_feature_flag_rejects_with_403():
    voice_svc, _, _ = _build_test_voice_service(enabled=False)
    with pytest.raises(HTTPException) as exc_info:
        await voice_svc.create_realtime_session(OWNER_A)
    assert exc_info.value.status_code == 403


@pytest.mark.anyio
async def test_missing_api_key_rejects_with_503():
    voice_svc, _, _ = _build_test_voice_service(api_key=None)
    with pytest.raises(HTTPException) as exc_info:
        await voice_svc.create_realtime_session(OWNER_A)
    assert exc_info.value.status_code == 503


@pytest.mark.anyio
async def test_daily_voice_quota_exceeded_rejects_with_429():
    voice_svc, _, _ = _build_test_voice_service(max_daily=2)
    # 2 allowed sessions
    await voice_svc.create_realtime_session(OWNER_A)
    await asyncio.sleep(0.02)
    await voice_svc.create_realtime_session(OWNER_A)

    # 3rd session must be rejected with 429
    await asyncio.sleep(0.02)
    with pytest.raises(HTTPException) as exc_info:
        await voice_svc.create_realtime_session(OWNER_A)
    assert exc_info.value.status_code == 429


@pytest.mark.anyio
async def test_daily_voice_duration_minutes_quota_exceeded_rejects_with_429():
    manager = VoiceSessionManager(
        db_path=":memory:",
        max_daily_sessions_per_student=10,
        max_daily_seconds_per_student=60,  # 1 minute limit for testing
        min_seconds_between_starts=0.01,
    )
    voice_svc, _, _ = _build_test_voice_service()
    voice_svc._session_manager = manager

    # Session 1 starts and consumes 50 seconds
    await voice_svc.create_realtime_session(OWNER_A)
    manager.record_duration(OWNER_A, 50.0)

    # Session 2 starts and consumes 20 seconds (exceeding 60s total)
    await asyncio.sleep(0.02)
    await voice_svc.create_realtime_session(OWNER_A)
    manager.record_duration(OWNER_A, 20.0)

    # Session 3 must be blocked because 70s > 60s max allowed
    await asyncio.sleep(0.02)
    with pytest.raises(HTTPException) as exc_info:
        await voice_svc.create_realtime_session(OWNER_A)
    assert exc_info.value.status_code == 429
    assert "دقائق" in str(exc_info.value.detail)


@pytest.mark.anyio
async def test_server_authoritative_session_timing_and_manipulation_protection():
    manager = VoiceSessionManager(
        db_path=":memory:",
        max_duration_seconds=900,
        max_daily_seconds_per_student=3600,
    )
    # Register session
    manager.register_session(
        session_id="sess_timing_1",
        student_user_id=OWNER_A,
        university_id=INST_A,
        thread_id=None,
    )
    # Simulate that server created_at was 40 seconds ago
    with manager._lock:
        conn = manager._get_connection()
        conn.execute(
            "UPDATE voice_active_sessions SET created_at = created_at - 40.0 WHERE session_id = 'sess_timing_1'"
        )

    # Client tries to under-report duration drastically (claims 2.0s when 40s elapsed)
    # The server detects manipulation (>25% lower and >10s gap) and enforces server elapsed (~40s)
    duration_recorded = manager.end_session(OWNER_A, "sess_timing_1", actual_duration_seconds=2.0)
    assert duration_recorded >= 40.0

    # Verify duration was recorded in daily usage
    daily_duration = manager.get_daily_duration_seconds(OWNER_A)
    assert daily_duration >= 40.0


@pytest.mark.anyio
async def test_abandoned_session_cleanup_and_concurrency_release():
    manager = VoiceSessionManager(
        db_path=":memory:",
        max_duration_seconds=60,
        inactivity_timeout_seconds=5.0,  # 5s inactivity timeout
    )
    # Register session
    state = manager.register_session(
        session_id="sess_abandoned_1",
        student_user_id=OWNER_A,
        university_id=INST_A,
        thread_id=None,
    )
    assert state.is_active is True

    # Simulate that 10 seconds elapsed without any activity (inactivity timeout exceeded)
    with manager._lock:
        conn = manager._get_connection()
        conn.execute(
            "UPDATE voice_active_sessions SET created_at = created_at - 10.0, last_activity_at = last_activity_at - 10.0 WHERE session_id = 'sess_abandoned_1'"
        )

    # Calling cleanup_expired cleans up the abandoned session
    cleaned = manager.cleanup_expired()
    assert cleaned == 1

    # Active session is now closed, concurrency released
    active = manager.get_active_session(OWNER_A)
    assert active is None

    # Elapsed time was server-authoritatively recorded in daily duration
    daily_duration = manager.get_daily_duration_seconds(OWNER_A)
    assert daily_duration >= 10.0


@pytest.mark.anyio
async def test_gpt_live_delegation_payload_and_fallback_model_support():
    captured_payloads = []

    async def capturing_handler(request: httpx.Request) -> httpx.Response:
        captured_payloads.append((request.url.path, json.loads(request.content.decode())))
        if request.url.path == "/v1/live/sessions":
            return httpx.Response(
                200,
                json={
                    "id": "sess_live_456",
                    "model": "gpt-live-1",
                    "transport": {
                        "type": "webrtc",
                        "sdp": "v=0\r\no=OpenAI ...",
                    },
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "sess_realtime_789",
                "model": "gpt-realtime-2.1",
                "client_secret": {"value": EPHEMERAL_KEY},
            },
        )

    # 1. Test GPT-Live server-mediated session payload
    voice_svc, _, _ = _build_test_voice_service(transport_handler=capturing_handler)
    session = await voice_svc.create_realtime_session(OWNER_A, sdp_offer="v=0\r\no=Browser ...")

    assert len(captured_payloads) == 1
    path, payload = captured_payloads[0]
    assert path == "/v1/live/sessions"
    assert payload["session"]["model"] == "gpt-live-1"
    assert payload["session"]["delegation"] == {"type": "client"}
    assert payload["session"]["audio"] == {"output": {"voice": "alloy"}}
    # Strict assertion: legacy Realtime fields must NOT be present in GPT-Live session payload
    assert "voice" not in payload["session"], "session.voice is unsupported; must be audio.output.voice"
    assert "modalities" not in payload["session"], "session.modalities is unsupported in Live API"
    assert "turn_detection" not in payload["session"], "session.turn_detection is unsupported in Live API"
    assert payload["transport"]["sdp"] == "v=0\r\no=Browser ..."
    assert session["endpoint_type"] == "live"
    assert session["sdp_answer"] == "v=0\r\no=OpenAI ..."

    # 2. Test Fallback Model (gpt-realtime-2.1)
    fallback_svc, _, _ = _build_test_voice_service(transport_handler=capturing_handler)
    fallback_svc._model = "gpt-realtime-2.1"
    fallback_session = await fallback_svc.create_realtime_session(OWNER_A)

    assert len(captured_payloads) == 2
    f_path, f_payload = captured_payloads[1]
    assert f_path == "/v1/realtime/sessions"
    assert f_payload["model"] == "gpt-realtime-2.1"
    assert len(f_payload["tools"]) == 15
    assert fallback_session["endpoint_type"] == "realtime"
    assert fallback_session["client_secret"] == EPHEMERAL_KEY


@pytest.mark.anyio
async def test_client_delegation_executes_academic_tool_deterministically():
    voice_svc, advisor_svc, _ = _build_test_voice_service()
    await voice_svc.create_realtime_session(OWNER_A, thread_id="test-thread-id")

    # Delegate get_remaining_requirements
    result = await voice_svc.execute_delegated_tool(
        student_user_id=OWNER_A,
        call_id="call_req_123",
        tool_name="get_remaining_requirements",
        arguments="{}",
        thread_id="test-thread-id",
    )

    assert result["call_id"] == "call_req_123"
    assert result["tool_name"] == "get_remaining_requirements"
    assert result["ok"] is True
    assert result["output"]["remaining_credit_hours"] == 12
    assert "مشروع التخرج 2" in result["output"]["requirements_left"]


@pytest.mark.anyio
async def test_client_delegation_executes_dialect_switch_and_updates_session_state():
    voice_svc, _, store = _build_test_voice_service()
    await voice_svc.create_realtime_session(OWNER_A, thread_id="test-thread-id")

    result = await voice_svc.execute_delegated_tool(
        student_user_id=OWNER_A,
        call_id="call_dialect_456",
        tool_name="switch_dialect",
        arguments=json.dumps({"dialect": "jordanian"}),
        thread_id="test-thread-id",
    )

    assert result["ok"] is True
    assert result["output"]["dialect"] == "jordanian"

    # Verify session manager recorded dialect update
    session_state = voice_svc._session_manager.get_active_session(OWNER_A)
    assert session_state is not None
    assert session_state.arabic_dialect == "jordanian"
    assert session_state.dialect_source == "explicit_user_request"


@pytest.mark.anyio
async def test_sync_completed_turn_persists_confirmed_speech_into_conversation_thread():
    voice_svc, _, store = _build_test_voice_service()
    turn_id = uuid4()

    res = await voice_svc.sync_completed_turn(
        student_user_id=OWNER_A,
        thread_id="test-thread-id",
        user_transcript="قديش ضايل علي ساعات للتخرج؟",
        assistant_transcript="بحسب خطتك الدراسية، يتبقى عليك 12 ساعة معتمدة فقط.",
        client_turn_id=turn_id,
    )

    assert res["synced"] is True
    assert len(store.messages) == 2
    user_msg = store.messages[0]
    advisor_msg = store.messages[1]

    assert user_msg["role"] == "USER"
    assert user_msg["content"] == "قديش ضايل علي ساعات للتخرج؟"
    assert user_msg["provenance"] == "USER_SPOKEN"

    assert advisor_msg["role"] == "ASSISTANT"
    assert advisor_msg["content"] == "بحسب خطتك الدراسية، يتبقى عليك 12 ساعة معتمدة فقط."
    assert advisor_msg["provenance"] == "VOICE_ADVISOR"


# ══════════════════════════════════════════════════════════════════════════
# FastAPI End-to-End Route Integration Tests
# ══════════════════════════════════════════════════════════════════════════

def test_api_route_requires_authentication():
    client = TestClient(app)
    response = client.post("/api/v1/me/voice/session", json={})
    assert response.status_code == 401


def test_api_route_get_status_authorized():
    voice_svc, _, _ = _build_test_voice_service()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id=OWNER_A)
    app.dependency_overrides[get_voice_service] = lambda: voice_svc

    try:
        client = TestClient(app)
        response = client.get("/api/v1/me/voice/status")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["configured"] is True
        assert data["remaining_daily_quota"] == 5
    finally:
        app.dependency_overrides.clear()


def test_api_route_session_establishment_and_delegation_flow():
    voice_svc, _, _ = _build_test_voice_service()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id=OWNER_A)
    app.dependency_overrides[get_voice_service] = lambda: voice_svc

    try:
        client = TestClient(app)

        # 1. Create WebRTC Voice Session via server-mediated SDP offer
        session_res = client.post("/api/v1/me/voice/session", json={"sdp_offer": "v=0\r\no=Browser ..."})
        assert session_res.status_code == 200
        session_data = session_res.json()
        assert session_data["sdp_answer"] == "v=0\r\no=OpenAI ..."
        assert session_data["session_id"] == "sess_live_test_123"
        assert session_data["endpoint_type"] == "live"

        # 2. Client Delegation Tool Call
        delegate_res = client.post(
            "/api/v1/me/voice/delegate",
            json={
                "call_id": "call_course_789",
                "tool_name": "get_course_eligibility",
                "arguments": json.dumps({"course_reference": "CS401"}),
            },
        )
        assert delegate_res.status_code == 200
        del_data = delegate_res.json()
        assert del_data["call_id"] == "call_course_789"
        assert del_data["output"]["eligible"] is True
        assert del_data["summary_text"] is not None

        # 3. End Session with actual duration reconciliation
        end_res = client.post(
            "/api/v1/me/voice/end-session",
            json={"session_id": session_data["session_id"], "actual_duration_seconds": 45.0},
        )
        assert end_res.status_code == 200
        assert end_res.json() == {"ok": True}
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_sync_completed_turn_does_not_double_count_duration():
    """Verify that syncing speech turns does not record duration into quota,
    leaving session termination wall-clock duration as the single authoritative source.
    """
    voice_svc, _, store = _build_test_voice_service()
    session = await voice_svc.create_realtime_session(OWNER_A, thread_id="test-thread-id")
    manager = voice_svc._session_manager

    # Sync multiple conversational turns with large text
    for _ in range(4):
        await voice_svc.sync_completed_turn(
            student_user_id=OWNER_A,
            thread_id="test-thread-id",
            user_transcript="هذا سؤال طويل جداً يستغرق وقتاً طويلاً في التحدث " * 5,
            assistant_transcript="وهذه إجابة مفصلة جداً تستغرق وقتاً طويلاً أيضاً " * 5,
            client_turn_id=uuid4(),
        )

    # Prior to ending the session, total_seconds in usage table should be 0 (no turn estimates billed!)
    today = manager._today_utc()
    conn = manager._get_connection()
    try:
        row = conn.execute(
            "SELECT total_seconds FROM voice_daily_usage WHERE student_user_id = ? AND date_str_utc = ?",
            (OWNER_A, today),
        ).fetchone()
        persisted_usage_seconds = float(row["total_seconds"]) if row else 0.0
        assert persisted_usage_seconds == 0.0, "Completed turns must NOT insert estimated durations into daily usage table"
    finally:
        manager._close_connection(conn)

    # Simulate 25 seconds elapsed on server
    with manager._lock:
        conn = manager._get_connection()
        conn.execute(
            "UPDATE voice_active_sessions SET created_at = created_at - 25.0 WHERE session_id = ?",
            (session["session_id"],),
        )

    # Now end session with 25.0 seconds actual duration
    recorded = manager.end_session(OWNER_A, session_id=session["session_id"], actual_duration_seconds=25.0)
    assert recorded == pytest.approx(25.0, abs=2.0)

    # Final daily duration should equal exactly the single authoritative session duration (~25s)
    daily_duration = manager.get_daily_duration_seconds(OWNER_A)
    assert daily_duration == pytest.approx(25.0, abs=2.0)
    assert daily_duration < 50.0, "Turn estimates must not double-count on top of session duration"


@pytest.mark.anyio
async def test_delegation_rejected_when_session_expired():
    """Verify that once a voice session is expired or closed, academic delegation is strictly rejected."""
    voice_svc, advisor_svc, _ = _build_test_voice_service()

    # 1. No active session at all
    res_no_sess = await voice_svc.execute_delegated_tool(
        student_user_id=OWNER_A,
        call_id="call_no_sess_1",
        tool_name="get_remaining_requirements",
        arguments="{}",
    )
    assert res_no_sess["ok"] is False
    assert res_no_sess["output"]["error"] == "SESSION_EXPIRED"
    assert "انتهت" in res_no_sess["summary_text"]

    # 2. Session created and then ended
    session = await voice_svc.create_realtime_session(OWNER_A, thread_id="test-thread-id")
    voice_svc._session_manager.end_session(OWNER_A, session_id=session["session_id"], actual_duration_seconds=10.0)

    res_ended = await voice_svc.execute_delegated_tool(
        student_user_id=OWNER_A,
        call_id="call_ended_2",
        tool_name="get_remaining_requirements",
        arguments="{}",
    )
    assert res_ended["ok"] is False
    assert res_ended["output"]["error"] == "SESSION_EXPIRED"


@pytest.mark.anyio
async def test_end_session_is_idempotent_and_protects_against_duplicate_accounting():
    """Verify that multiple or redundant calls to end_session do not bill duration multiple times."""
    manager = VoiceSessionManager(db_path=":memory:", min_seconds_between_starts=0.01)
    manager.register_session(
        session_id="sess_idemp_1",
        student_user_id=OWNER_A,
        university_id=INST_A,
        thread_id="t-1",
        duration_seconds=900,
    )

    # Simulate 40 seconds elapsed on server
    with manager._lock:
        conn = manager._get_connection()
        conn.execute(
            "UPDATE voice_active_sessions SET created_at = created_at - 40.0 WHERE session_id = 'sess_idemp_1'"
        )

    # First termination
    dur1 = manager.end_session(OWNER_A, session_id="sess_idemp_1", actual_duration_seconds=40.0)
    assert dur1 == pytest.approx(40.0, abs=1.0)
    assert manager.get_daily_duration_seconds(OWNER_A) == pytest.approx(40.0, abs=1.0)

    # Redundant second termination
    dur2 = manager.end_session(OWNER_A, session_id="sess_idemp_1", actual_duration_seconds=40.0)
    assert dur2 == 0.0, "Subsequent termination of already-ended session must return 0 duration"

    # Redundant third termination without session_id
    dur3 = manager.end_session(OWNER_A, actual_duration_seconds=40.0)
    assert dur3 == 0.0

    # Total recorded seconds must remain unchanged at 40.0s (not 80s or 120s!)
    assert manager.get_daily_duration_seconds(OWNER_A) == pytest.approx(40.0, abs=1.0)


@pytest.mark.anyio
async def test_cleanup_expired_and_inactivity_abandonment():
    """Verify server-side cleanup of sessions that reach deadline or are abandoned without activity."""
    manager = VoiceSessionManager(
        db_path=":memory:",
        max_duration_seconds=10,
        inactivity_timeout_seconds=5,
        min_seconds_between_starts=0.01,
    )
    # Register session
    manager.register_session(
        session_id="sess_stale_1",
        student_user_id=OWNER_A,
        university_id=INST_A,
        thread_id="t-1",
        duration_seconds=10,
    )
    assert manager.get_active_session(OWNER_A) is not None

    # Simulate passing of time by manipulating created_at and last_activity_at in DB
    past_time = time.time() - 20.0
    conn = manager._get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE voice_active_sessions SET created_at = ?, last_activity_at = ?, expires_at = ? WHERE student_user_id = ?",
                (past_time, past_time, past_time + 10.0, OWNER_A),
            )
    finally:
        manager._close_connection(conn)

    # Calling cleanup_expired should reap the session and record up to max_duration (10s)
    cleaned = manager.cleanup_expired()
    assert cleaned == 1
    assert manager.get_active_session(OWNER_A) is None
    assert manager.get_daily_duration_seconds(OWNER_A) == pytest.approx(10.0, abs=1.0)


# ══════════════════════════════════════════════════════════════════════════
# Owner-Only Production Access Allowlist Tests
# ══════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_owner_allowlist_permits_authorized_user():
    """Verify that when allowed_user_ids is set, authorized user can access voice."""
    voice_svc, _, _ = _build_test_voice_service(
        allowed_user_ids=f"{OWNER_A}, 22222222-2222-2222-2222-222222222222",
        app_env="production",
    )
    assert voice_svc.is_user_authorized(OWNER_A) is True
    status = voice_svc.get_status(OWNER_A)
    assert status["is_authorized"] is True
    assert status["enabled"] is True

    session = await voice_svc.create_realtime_session(OWNER_A, sdp_offer="v=0\r\no=Browser ...")
    assert session["session_id"] == "sess_live_test_123"


@pytest.mark.anyio
async def test_owner_allowlist_rejects_unauthorized_user_with_403():
    """Verify that unauthorized user is blocked with 403 on all voice operations."""
    unauthorized_id = "99999999-9999-9999-9999-999999999999"
    voice_svc, _, _ = _build_test_voice_service(
        allowed_user_ids=OWNER_A,
        app_env="production",
    )
    assert voice_svc.is_user_authorized(unauthorized_id) is False

    status = voice_svc.get_status(unauthorized_id)
    assert status["is_authorized"] is False

    with pytest.raises(HTTPException) as exc_sess:
        await voice_svc.create_realtime_session(unauthorized_id, sdp_offer="v=0\r\no=Browser ...")
    assert exc_sess.value.status_code == 403

    res_del = await voice_svc.execute_delegated_tool(
        student_user_id=unauthorized_id,
        call_id="call-unauth-1",
        tool_name="get_remaining_requirements",
        arguments="{}",
    )
    assert res_del["ok"] is False
    assert res_del["output"]["error"] == "FORBIDDEN"

    with pytest.raises(HTTPException) as exc_sync:
        await voice_svc.sync_completed_turn(
            student_user_id=unauthorized_id,
            thread_id="test-thread-id",
            user_transcript="سؤال غير مصرح به",
            assistant_transcript="رد غير مصرح به",
            client_turn_id=uuid4(),
        )
    assert exc_sync.value.status_code == 403


@pytest.mark.anyio
async def test_production_fails_closed_when_allowlist_empty():
    """In production, empty allowlist must deny all users safely."""
    voice_svc, _, _ = _build_test_voice_service(
        allowed_user_ids="",
        app_env="production",
    )
    assert voice_svc.is_user_authorized(OWNER_A) is False
    status = voice_svc.get_status(OWNER_A)
    assert status["is_authorized"] is False

    with pytest.raises(HTTPException) as exc:
        await voice_svc.create_realtime_session(OWNER_A, sdp_offer="v=0\r\no=Browser ...")
    assert exc.value.status_code == 403


def test_api_route_rejects_unauthorized_user():
    """Verify HTTP route behavior for unauthorized student."""
    unauthorized_id = "88888888-8888-8888-8888-888888888888"
    voice_svc, _, _ = _build_test_voice_service(
        allowed_user_ids=OWNER_A,
        app_env="production",
    )
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(user_id=unauthorized_id)
    app.dependency_overrides[get_voice_service] = lambda: voice_svc

    try:
        client = TestClient(app)

        # Status returns 200 with is_authorized=False so UI can hide button
        res_status = client.get("/api/v1/me/voice/status")
        assert res_status.status_code == 200
        assert res_status.json()["is_authorized"] is False

        # Session creation returns 403
        res_sess = client.post("/api/v1/me/voice/session", json={"sdp_offer": "v=0\r\n..."})
        assert res_sess.status_code == 403

        # Delegation returns structured rejection so WebRTC does not break
        res_del = client.post("/api/v1/me/voice/delegate", json={
            "call_id": "c1",
            "tool_name": "get_remaining_requirements",
            "arguments": "{}",
        })
        assert res_del.status_code == 200
        assert res_del.json()["ok"] is False
        assert res_del.json()["output"]["error"] == "FORBIDDEN"

        # Turn sync returns 403
        res_sync = client.post("/api/v1/me/voice/sync-turn", json={
            "thread_id": str(uuid4()),
            "user_transcript": "test",
            "assistant_transcript": "test",
            "client_turn_id": str(uuid4()),
        })
        assert res_sync.status_code == 403

        # End session returns 403
        res_end = client.post("/api/v1/me/voice/end-session", json={
            "session_id": "sess_1",
            "actual_duration_seconds": 10.0,
        })
        assert res_end.status_code == 403
    finally:
        app.dependency_overrides.clear()



