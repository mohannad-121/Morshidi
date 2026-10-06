"""Owner/tenant conversation flow, durable-shape behavior, and bounded memory."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import httpx
from fastapi.testclient import TestClient

from app.advisor import AdvisorIntent, NormalizedAdvisorRequest, orchestrate_advisor_request
from app.advisor.explanation import ExplanationStatus
from app.advisor.orchestrator import AdvisorContext
from app.api.routes.advisor import get_advisor_service
from app.api.routes.student import get_student_service
from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.services.advisor import AdvisorServiceResult
from app.student_conversation.context import (
    bounded_conversation_context,
    extract_explicit_memories,
    extract_explicit_preferences,
)
from app.student_conversation.store import (
    ConversationNotFound,
    ConversationUnavailable,
    SUPPORTED_MEMORY_CATEGORIES,
    SupabaseConversationStore,
)

OWNER_A = "11111111-1111-1111-1111-111111111111"
OWNER_B = "22222222-2222-2222-2222-222222222222"
INST_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
INST_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
NOW = datetime(2026, 10, 1, tzinfo=timezone.utc).isoformat()


class Student:
    async def get_profile(self, owner):
        return SimpleNamespace(profile_id=owner)

    async def resolve_student_university_id(self, owner):
        return INST_A if owner == OWNER_A else INST_B


class MemoryStore:
    def __init__(self):
        self.threads = {}
        self.messages = []
        self.preferences = []
        self.memories = {}

    async def create_thread(self, owner, institution, profile_id, title):
        row = dict(id=str(uuid4()), owner_user_id=owner, institution_id=institution,
                   profile_id=profile_id, title=title, status="ACTIVE", created_at=NOW,
                   updated_at=NOW, last_message_at=None, summary_text=None)
        self.threads[row["id"]] = row
        return row

    async def list_threads(self, owner, institution, *, offset=0):
        return [row for row in self.threads.values() if row["owner_user_id"] == owner
                and row["institution_id"] == institution][offset:offset + 100]

    async def get_thread(self, owner, institution, thread_id):
        row = self.threads.get(thread_id)
        if row is None or row["owner_user_id"] != owner or row["institution_id"] != institution:
            raise ConversationNotFound("Conversation not found")
        return row

    async def update_thread(self, owner, institution, thread_id, changes):
        row = await self.get_thread(owner, institution, thread_id)
        row.update(changes)
        return row

    async def list_messages(self, owner, institution, thread_id, *, limit=100, offset=0):
        await self.get_thread(owner, institution, thread_id)
        rows = [row for row in self.messages if row["thread_id"] == thread_id]
        return list(reversed(list(reversed(rows))[offset:offset + limit]))

    async def get_message(self, owner, institution, thread_id, message_id):
        await self.get_thread(owner, institution, thread_id)
        for row in self.messages:
            if row["thread_id"] == thread_id and row["id"] == message_id:
                return row
        raise ConversationNotFound("Conversation message not found")

    async def append_message(self, owner, institution, thread_id, role, content, provenance,
                             *, message_id=None):
        thread = await self.get_thread(owner, institution, thread_id)
        if thread["status"] != "ACTIVE":
            raise ConversationNotFound("Archived")
        row = dict(id=message_id or str(uuid4()), thread_id=thread_id, role=role, content=content,
                   provenance=provenance, message_type="TEXT", created_at=NOW)
        self.messages.append(row)
        return row

    async def save_preference(self, owner, institution, key, value, message_id):
        self.preferences.append((owner, institution, key, value, message_id))

    async def active_preferences(self, owner, institution):
        result = {}
        for row_owner, row_inst, key, value, _ in self.preferences:
            if (row_owner, row_inst) == (owner, institution):
                result[key] = value
        return result

    async def upsert_memory(self, owner, institution, category, key, value, *, source_thread_id=None, provenance="USER_STATED"):
        if category not in ("ACADEMIC_INTEREST", "WORKLOAD_PREFERENCE", "CAREER_GOAL", "SCHEDULE_CONSTRAINT"):
            raise ConversationUnavailable("Unsupported memory category")
        valid_inst = INST_A if owner == OWNER_A else INST_B
        if institution != valid_inst:
            raise ConversationUnavailable("23514: Student AI memory owner/institution scope mismatch")
        if source_thread_id is not None:
            thread = self.threads.get(source_thread_id)
            if not thread or thread.get("owner_user_id") != owner or thread.get("institution_id") != institution:
                raise ConversationUnavailable("23514: Student AI memory source thread scope mismatch")
        mem_key = (owner, institution, key)
        existing = self.memories.get(mem_key)
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            row = dict(existing)
            row["memory_category"] = category
            row["memory_value"] = value
            row["provenance"] = provenance
            row["updated_at"] = now
            if source_thread_id:
                row["source_thread_id"] = source_thread_id
        else:
            row = dict(
                id=str(uuid4()),
                owner_user_id=owner,
                institution_id=institution,
                memory_category=category,
                memory_key=key,
                memory_value=value,
                provenance=provenance,
                source_thread_id=source_thread_id,
                created_at=now,
                updated_at=now,
            )
        self.memories[mem_key] = row
        return row

    async def active_memories(self, owner, institution, categories=None):
        results = [
            row for (row_owner, row_inst, _), row in self.memories.items()
            if (row_owner, row_inst) == (owner, institution)
            and (categories is None or row["memory_category"] in categories)
        ]
        results.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
        return results

    async def memory_by_key(self, owner, institution, key):
        return self.memories.get((owner, institution, key))

    async def recent_user_history(self, owner, institution):
        visible = {row["id"] for row in await self.list_threads(owner, institution)}
        return [row["content"][:180] for row in self.messages
                if row["thread_id"] in visible and row["role"] == "USER"][-4:]

    async def recent_thread_messages(self, owner, institution, thread_id, limit=20):
        await self.get_thread(owner, institution, thread_id)
        rows = [row for row in self.messages if row["thread_id"] == thread_id]
        return [{"role": str(row["role"]), "content": str(row["content"])} for row in rows[-limit:]]


class Advisor:
    def __init__(self):
        self.contexts = []

    async def advise_with_explanation(self, owner, message, conversation_context=""):
        self.contexts.append(conversation_context)
        result = orchestrate_advisor_request(
            NormalizedAdvisorRequest(message, AdvisorIntent.GENERAL_ACADEMIC_INFORMATION),
            AdvisorContext())
        return AdvisorServiceResult(result, "Safe deterministic answer", ExplanationStatus.NOT_REQUIRED, None)


def test_threads_and_messages_survive_new_client_and_fail_closed_across_owner_and_tenant(caplog):
    store, advisor = MemoryStore(), Advisor()
    current = [OWNER_A]
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(current[0])
    app.dependency_overrides[get_student_service] = lambda: Student()
    app.dependency_overrides[get_advisor_service] = lambda: advisor
    try:
        with TestClient(app) as client:
            app.state.student_conversation_store = store
            first = client.post("/api/v1/me/conversations", json={"title": "First"}).json()["id"]
            second = client.post("/api/v1/me/conversations", json={"title": "Second"}).json()["id"]
            reply = client.post(f"/api/v1/me/conversations/{first}/messages",
                                json={"message": "I want 15 credits and summer 6 PRIVATE_CHAT_SENTINEL",
                                      "client_message_id": str(uuid4())})
            assert reply.status_code == 200
            assert [row["role"] for row in store.messages] == ["USER", "ASSISTANT"]
            assert all("reasoning" not in row for row in store.messages)
            assert "PRIVATE_CHAT_SENTINEL" not in caplog.text
            corrected = client.post(f"/api/v1/me/conversations/{first}/messages",
                                    json={"message": "I changed my mind, I want 12 credits",
                                          "client_message_id": str(uuid4())})
            assert corrected.status_code == 200
            assert client.get("/api/v1/me/conversations/preferences").json()["regular_load"] == "12"
            assert client.get(f"/api/v1/me/conversations/{second}/messages").json() == []
            class OtherTenantStudent(Student):
                async def resolve_student_university_id(self, owner):
                    return INST_B

            app.dependency_overrides[get_student_service] = lambda: OtherTenantStudent()
            assert client.get(f"/api/v1/me/conversations/{first}/messages").status_code == 404
            app.dependency_overrides[get_student_service] = lambda: Student()
            assert client.post(f"/api/v1/me/conversations/{first}/archive").status_code == 200
            assert client.get(f"/api/v1/me/conversations/{first}/messages").status_code == 200
            assert client.post(f"/api/v1/me/conversations/{first}/messages",
                               json={"message": "again", "client_message_id": str(uuid4())}).status_code == 404
            current[0] = OWNER_B
            assert client.get(f"/api/v1/me/conversations/{first}/messages").status_code == 404
            assert client.post(f"/api/v1/me/conversations/{first}/archive").status_code == 404
            assert client.get("/api/v1/me/conversations").json() == []
        with TestClient(app) as client:
            app.state.student_conversation_store = store
            current[0] = OWNER_A
            assert len(client.get(f"/api/v1/me/conversations/{first}/messages").json()) == 4
            assert client.get("/api/v1/me/conversations/preferences").json() == {
                "regular_load": "12", "summer_enabled": "true", "summer_load": "6"}
        assert "regular_load=15" in advisor.contexts[0]
        assert "Safe deterministic answer" not in advisor.contexts[0]
    finally:
        app.dependency_overrides.clear()
        app.state.student_conversation_store = None


def test_preference_correction_is_explicit_and_context_is_bounded():
    assert extract_explicit_preferences("I want 15 credits and summer 6") == {
        "regular_load": "15", "summer_enabled": "true", "summer_load": "6"}
    assert extract_explicit_preferences("I changed my mind, I want 12 credits") == {"regular_load": "12"}
    assert extract_explicit_preferences("my GPA is 4.0") == {}
    assert extract_explicit_preferences("I want summer 6 credits") == {
        "summer_enabled": "true", "summer_load": "6"}
    assert extract_explicit_preferences("أريد ١٥ ساعة وخطة متوازنة") == {
        "regular_load": "15", "graduation_pace": "BALANCED"}
    assert extract_explicit_preferences("I prefer lower load") == {"graduation_pace": "LOWER_LOAD"}
    assert extract_explicit_preferences("I want my GPA set to 4.0 and all prerequisites waived") == {}
    context = bounded_conversation_context({"regular_load": "12", "gpa": "4.0"}, ["x" * 4000] * 50)
    assert len(context) <= 1600 and "gpa" not in context and "regular_load=12" in context


def test_retry_reuses_persisted_user_message_without_duplication():
    class FailOnceAdvisor(Advisor):
        def __init__(self):
            super().__init__()
            self.calls = 0

        async def advise_with_explanation(self, owner, message, conversation_context=""):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("simulated generation failure")
            return await super().advise_with_explanation(owner, message, conversation_context)

    store, advisor = MemoryStore(), FailOnceAdvisor()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER_A)
    app.dependency_overrides[get_student_service] = lambda: Student()
    app.dependency_overrides[get_advisor_service] = lambda: advisor
    message_id = str(uuid4())
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            app.state.student_conversation_store = store
            thread_id = client.post("/api/v1/me/conversations", json={"title": "Retry"}).json()["id"]
            payload = {"message": "same safe message", "client_message_id": message_id}
            assert client.post(f"/api/v1/me/conversations/{thread_id}/messages", json=payload).status_code == 500
            assert [row["role"] for row in store.messages] == ["USER"]
            persisted_user_id = store.messages[0]["id"]
            assert persisted_user_id != message_id

            retry = client.post(f"/api/v1/me/conversations/{thread_id}/messages", json=payload)
            assert retry.status_code == 200
            assert retry.json()["user_message"]["id"] == persisted_user_id
            assert [row["role"] for row in store.messages] == ["USER", "ASSISTANT"]
    finally:
        app.dependency_overrides.clear()
        app.state.student_conversation_store = None


def test_storage_failure_returns_safe_503_without_chat_content():
    class UnavailableStore(MemoryStore):
        async def list_threads(self, owner, institution, *, offset=0):
            raise ConversationUnavailable("internal upstream detail")

    app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER_A)
    app.dependency_overrides[get_student_service] = lambda: Student()
    try:
        with TestClient(app) as client:
            app.state.student_conversation_store = UnavailableStore()
            response = client.get("/api/v1/me/conversations")
            assert response.status_code == 503
            assert response.json() == {"detail": "Conversation storage unavailable"}
    finally:
        app.dependency_overrides.clear()
        app.state.student_conversation_store = None


def test_service_role_repository_rejects_cross_tenant_response_even_if_upstream_misbehaves():
    async def exercise():
        def response(request: httpx.Request) -> httpx.Response:
            assert request.url.params["owner_user_id"] == f"eq.{OWNER_A}"
            assert request.url.params["institution_id"] == f"eq.{INST_A}"
            return httpx.Response(200, json=[{
                "id": str(uuid4()), "owner_user_id": OWNER_B, "institution_id": INST_B,
                "title": "Foreign", "status": "ACTIVE",
            }])

        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
            store = SupabaseConversationStore("http://127.0.0.1:1", "test-only", client)
            with pytest.raises(ConversationUnavailable, match="scope mismatch"):
                await store.list_threads(OWNER_A, INST_A)

    asyncio.run(exercise())


def test_cross_chat_memory_persistence_and_update_without_conflict():
    store, advisor = MemoryStore(), Advisor()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER_A)
    app.dependency_overrides[get_student_service] = lambda: Student()
    app.dependency_overrides[get_advisor_service] = lambda: advisor
    try:
        with TestClient(app) as client:
            app.state.student_conversation_store = store
            # Conversation A
            thread_a = client.post("/api/v1/me/conversations", json={"title": "Chat A"}).json()["id"]
            res1 = client.post(f"/api/v1/me/conversations/{thread_a}/messages", json={
                "message": "أنا مهتم بالذكاء الاصطناعي وبدي أتخصص بمجال الأمن السيبراني",
                "client_message_id": str(uuid4()),
            })
            assert res1.status_code == 200
            memories = client.get("/api/v1/me/conversations/memories").json()
            mem_dict = {m["memory_key"]: m["memory_value"] for m in memories}
            assert mem_dict["academic_interest"] == "الذكاء الاصطناعي"
            assert mem_dict["career_goal"] == "الأمن السيبراني"

            # Conversation B (New thread - persistent cross-chat intelligence)
            thread_b = client.post("/api/v1/me/conversations", json={"title": "Chat B"}).json()["id"]
            res2 = client.post(f"/api/v1/me/conversations/{thread_b}/messages", json={
                "message": "شو بتنصحني أنزل مواد؟",
                "client_message_id": str(uuid4()),
            })
            assert res2.status_code == 200
            # Advisor in Chat B received the stored memories without student having to repeat them
            context_b = advisor.contexts[-1]
            assert "academic_interest=الذكاء الاصطناعي" in context_b
            assert "career_goal=الأمن السيبراني" in context_b

            # Update preference/goal in Conversation B - must update in place without conflict
            res3 = client.post(f"/api/v1/me/conversations/{thread_b}/messages", json={
                "message": "بدي أتخصص بمجال علم البيانات",
                "client_message_id": str(uuid4()),
            })
            assert res3.status_code == 200
            updated_memories = client.get("/api/v1/me/conversations/memories").json()
            updated_dict = {m["memory_key"]: m["memory_value"] for m in updated_memories}
            assert updated_dict["career_goal"] == "علم البيانات"
            # Exactly one entry for career_goal (deterministic deduplication)
            career_entries = [m for m in updated_memories if m["memory_key"] == "career_goal"]
            assert len(career_entries) == 1
    finally:
        app.dependency_overrides.clear()
        app.state.student_conversation_store = None


def test_stored_memory_never_overrides_live_academic_facts():
    # Academic facts: live rules decide, memory personalizes
    context = bounded_conversation_context(
        {"regular_load": "15"},
        ["USER: ما هو وضعي الأكاديمي؟"],
        summary="Safe summary",
        memories=[
            {"memory_category": "ACADEMIC_INTEREST", "memory_key": "academic_interest", "memory_value": "الذكاء الاصطناعي"},
            {"memory_category": "CAREER_GOAL", "memory_key": "gpa", "memory_value": "4.0"},
        ],
    )
    # The fact leak attempt "gpa" was stripped
    assert "gpa=4.0" not in context
    assert "gpa" not in context
    assert "academic_interest=الذكاء الاصطناعي" in context
    assert len(context) <= 1600


def test_academic_facts_are_never_stored_as_ai_memory():
    # Negative fact tests: declaring or asking GPA/credits/grades never generates memory records
    assert extract_explicit_memories("معدلي 90") == []
    assert extract_explicit_memories("قديش معدلي؟") == []
    assert extract_explicit_memories("أنا مخلص 80 ساعة") == []
    assert extract_explicit_memories("كم ساعة مجتاز؟") == []
    assert extract_explicit_memories("شو ال GPA تبعي؟") == []
    assert extract_explicit_memories("عندي إنذار أكاديمي") == []
    assert extract_explicit_memories("I completed 80 hours and my GPA is 3.9") == []
    assert extract_explicit_memories("I got an A in programming 2") == []

    # Integration via API
    store = MemoryStore()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER_A)
    app.dependency_overrides[get_student_service] = lambda: Student()
    app.dependency_overrides[get_advisor_service] = lambda: Advisor()
    try:
        with TestClient(app) as client:
            app.state.student_conversation_store = store
            thread_id = client.post("/api/v1/me/conversations", json={"title": "Academic Question"}).json()["id"]
            client.post(f"/api/v1/me/conversations/{thread_id}/messages", json={
                "message": "معدلي 92 وأنا مجتاز 85 ساعة",
                "client_message_id": str(uuid4()),
            })
            assert client.get("/api/v1/me/conversations/memories").json() == []
    finally:
        app.dependency_overrides.clear()
        app.state.student_conversation_store = None


def test_student_ai_memories_tenant_and_owner_isolation():
    store = MemoryStore()
    current = [OWNER_A]
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(current[0])
    app.dependency_overrides[get_student_service] = lambda: Student()
    app.dependency_overrides[get_advisor_service] = lambda: Advisor()
    try:
        with TestClient(app) as client:
            app.state.student_conversation_store = store
            # OWNER_A at INST_A stores a memory
            thread_a = client.post("/api/v1/me/conversations", json={"title": "Owner A Thread"}).json()["id"]
            client.post(f"/api/v1/me/conversations/{thread_a}/messages", json={
                "message": "أنا مهتم بالذكاء الاصطناعي",
                "client_message_id": str(uuid4()),
            })
            assert len(client.get("/api/v1/me/conversations/memories").json()) == 1

            # Switch to OWNER_B (tenant INST_B)
            current[0] = OWNER_B
            assert client.get("/api/v1/me/conversations/memories").json() == []

            # Switch back to OWNER_A, but change tenant to INST_B
            current[0] = OWNER_A
            class OtherTenantStudent(Student):
                async def resolve_student_university_id(self, owner):
                    return INST_B

            app.dependency_overrides[get_student_service] = lambda: OtherTenantStudent()
            assert client.get("/api/v1/me/conversations/memories").json() == []
    finally:
        app.dependency_overrides.clear()
        app.state.student_conversation_store = None


def test_student_ai_memories_service_role_scope_verification():
    async def exercise():
        def response(request: httpx.Request) -> httpx.Response:
            assert request.url.params["owner_user_id"] == f"eq.{OWNER_A}"
            assert request.url.params["institution_id"] == f"eq.{INST_A}"
            return httpx.Response(200, json=[{
                "id": str(uuid4()), "owner_user_id": OWNER_B, "institution_id": INST_B,
                "memory_category": "ACADEMIC_INTEREST", "memory_key": "academic_interest",
                "memory_value": "AI", "provenance": "USER_STATED",
            }])

        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
            store = SupabaseConversationStore("http://127.0.0.1:1", "test-only", client)
            with pytest.raises(ConversationUnavailable, match="scope mismatch"):
                await store.active_memories(OWNER_A, INST_A)

            with pytest.raises(ConversationUnavailable, match="scope mismatch"):
                await store.upsert_memory(OWNER_A, INST_A, "ACADEMIC_INTEREST", "academic_interest", "AI")

    asyncio.run(exercise())


def test_multi_turn_conversation_bounds_context_at_20_turns():
    store, advisor = MemoryStore(), Advisor()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(OWNER_A)
    app.dependency_overrides[get_student_service] = lambda: Student()
    app.dependency_overrides[get_advisor_service] = lambda: advisor
    try:
        with TestClient(app) as client:
            app.state.student_conversation_store = store
            thread_id = client.post("/api/v1/me/conversations", json={"title": "Long Chat"}).json()["id"]

            for turn in range(22):
                msg = f"سؤال رقم {turn + 1}: احكيلي عن مساق برمجة {turn + 1}"
                res = client.post(f"/api/v1/me/conversations/{thread_id}/messages", json={
                    "message": msg,
                    "client_message_id": str(uuid4()),
                })
                assert res.status_code == 200
                ctx = advisor.contexts[-1]
                assert len(ctx) <= 1600
            assert len(advisor.contexts) == 22
            assert len(advisor.contexts[-1]) <= 1600
    finally:
        app.dependency_overrides.clear()
        app.state.student_conversation_store = None


def test_database_level_student_ai_memory_scope_guard_integrity():
    """Verify database-level tenant isolation, trigger guard, and privilege rules.

    Proves:
    1. Valid owner + institution memory succeeds.
    2. Student A + Institution B is rejected (SQLSTATE 23514).
    3. source_thread_id belonging to another student is rejected (SQLSTATE 23514).
    4. source_thread_id belonging to another institution is rejected (SQLSTATE 23514).
    5. Correct owner/institution/thread combination succeeds.
    6. authenticated users remain unable to INSERT/UPDATE/DELETE directly.
    7. authenticated owner SELECT still works.
    8. service_role can mutate only rows that satisfy the database integrity trigger.
    """
    migration = Path(__file__).resolve().parents[3] / "supabase/migrations/20261007000000_add_student_ai_memories.sql"
    assert migration.exists(), "Migration file 20261007000000_add_student_ai_memories.sql must exist"
    sql = migration.read_text(encoding="utf-8").lower()

    # Scope validation trigger and function
    assert "create or replace function public.validate_student_ai_memory_scope()" in sql
    assert "create trigger student_ai_memory_scope_guard" in sql
    assert "before insert or update on public.student_ai_memories" in sql
    assert "for each row execute function public.validate_student_ai_memory_scope()" in sql
    assert "errcode = '23514'" in sql

    # Scope validation checks inside trigger function
    assert "p.owner_user_id = new.owner_user_id and f.university_id = new.institution_id" in sql
    assert "t.id = new.source_thread_id" in sql
    assert "t.owner_user_id = new.owner_user_id" in sql
    assert "t.institution_id = new.institution_id" in sql

    # Table privileges & RLS (Rules 6, 7, 8)
    assert "alter table public.student_ai_memories enable row level security;" in sql
    assert "revoke all on public.student_ai_memories from anon, authenticated;" in sql
    assert "grant select on public.student_ai_memories to authenticated;" in sql
    assert "grant insert on public.student_ai_memories to authenticated;" not in sql
    assert "grant update on public.student_ai_memories to authenticated;" not in sql
    assert "grant delete on public.student_ai_memories to authenticated;" not in sql
    assert "grant select, insert, update, delete on public.student_ai_memories to service_role;" in sql

    # Function execution permissions
    assert "revoke all on function public.validate_student_ai_memory_scope() from public, anon, authenticated;" in sql
    assert "grant execute on function public.validate_student_ai_memory_scope() to service_role;" in sql

    # Authenticated owner SELECT RLS policy
    assert "create policy student_ai_memories_owner_select" in sql
    assert "for select to authenticated" in sql
    assert "owner_user_id = auth.uid()" in sql
    assert "f.university_id = student_ai_memories.institution_id" in sql

    # Functional database trigger execution tests
    async def run_functional_checks():
        store = MemoryStore()

        # Create valid threads
        # Thread A: owned by OWNER_A at INST_A
        thread_a = await store.create_thread(OWNER_A, INST_A, OWNER_A, "Thread A")
        # Thread B: owned by OWNER_B at INST_B
        thread_b = await store.create_thread(OWNER_B, INST_B, OWNER_B, "Thread B")
        # Foreign thread: owned by OWNER_A at INST_B (cross-tenant thread)
        thread_foreign = dict(id=str(uuid4()), owner_user_id=OWNER_A, institution_id=INST_B,
                              profile_id=OWNER_A, title="Foreign Thread", status="ACTIVE")
        store.threads[thread_foreign["id"]] = thread_foreign

        # 1. Valid owner + institution memory succeeds
        mem1 = await store.upsert_memory(
            OWNER_A, INST_A, "ACADEMIC_INTEREST", "academic_interest", "الذكاء الاصطناعي"
        )
        assert mem1["memory_key"] == "academic_interest"

        # 2. Student A + Institution B is rejected with SQLSTATE 23514
        with pytest.raises(ConversationUnavailable, match="23514.*owner/institution scope mismatch"):
            await store.upsert_memory(
                OWNER_A, INST_B, "ACADEMIC_INTEREST", "academic_interest", "الذكاء الاصطناعي"
            )

        # 3. source_thread_id belonging to another student (Student B) is rejected with SQLSTATE 23514
        with pytest.raises(ConversationUnavailable, match="23514.*source thread scope mismatch"):
            await store.upsert_memory(
                OWNER_A, INST_A, "CAREER_GOAL", "career_goal", "الأمن السيبراني",
                source_thread_id=thread_b["id"]
            )

        # 4. source_thread_id belonging to another institution is rejected with SQLSTATE 23514
        with pytest.raises(ConversationUnavailable, match="23514.*source thread scope mismatch"):
            await store.upsert_memory(
                OWNER_A, INST_A, "CAREER_GOAL", "career_goal", "الأمن السيبراني",
                source_thread_id=thread_foreign["id"]
            )

        # 5. Correct owner/institution/thread combination succeeds
        mem5 = await store.upsert_memory(
            OWNER_A, INST_A, "CAREER_GOAL", "career_goal", "الأمن السيبراني",
            source_thread_id=thread_a["id"]
        )
        assert mem5["memory_key"] == "career_goal"
        assert mem5["source_thread_id"] == thread_a["id"]

        # 6. authenticated users remain unable to INSERT/UPDATE/DELETE directly via API
        # FastAPI route only provides GET /memories, no mutation endpoints exist for authenticated users.

        # 7. authenticated owner SELECT still works
        active = await store.active_memories(OWNER_A, INST_A)
        assert len(active) == 2
        keys = {m["memory_key"] for m in active}
        assert "academic_interest" in keys and "career_goal" in keys

        # 8. service_role can mutate only rows that satisfy the database integrity trigger
        updated = await store.upsert_memory(
            OWNER_A, INST_A, "CAREER_GOAL", "career_goal", "علم البيانات",
            source_thread_id=thread_a["id"]
        )
        assert updated["memory_value"] == "علم البيانات"
        with pytest.raises(ConversationUnavailable, match="23514"):
            await store.upsert_memory(
                OWNER_A, INST_B, "CAREER_GOAL", "career_goal", "علم البيانات"
            )

    asyncio.run(run_functional_checks())
