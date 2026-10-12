"""Opt-in runtime proof for Student Intelligence V2 against Local Supabase only."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
import os
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.catalog.supabase_repository import SupabaseAcademicCatalogRepository
from app.services.eligibility import EligibilityService
from app.services.student import StudentService
from app.rules.models import AttemptOutcome
from app.student.models import PerformanceProvenance, PerformanceVerificationState
from app.student.supabase_repository import SupabaseStudentAcademicRepository
from app.student_intelligence.adaptive import (
    FAKE_UNIVERSITY_GRADING_POLICY_V1,
    GradePolicyRegistry,
)
from app.university_sync.grading_policy import grading_policy_source_reference
from app.student_intelligence.diagnostic import (
    ASSESSMENT_VERSION,
    QUESTIONS_BY_ID,
    AnswerEvidence,
    DiagnosticDomain,
    score_domain,
)
from app.student_intelligence.diagnostic_repository import SupabaseDiagnosticRepository
from app.student_intelligence.diagnostic_service import DiagnosticConflict, DiagnosticService
from app.student_intelligence.profile_v2 import build_student_intelligence_profile_v2


URL = os.getenv("MORSHIDI_LOCAL_SUPABASE_URL")
SERVER_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_SERVER_KEY")
ANON_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_ANON_KEY")
PLAN12 = os.getenv("MORSHIDI_LOCAL_STUDY_PLAN_ID", "10000000-0000-0000-0000-000000000005")
pytestmark = pytest.mark.skipif(
    not all((URL, SERVER_KEY, ANON_KEY)),
    reason="set local-only MORSHIDI_LOCAL_SUPABASE_* values",
)

ADMIN = {"apikey": SERVER_KEY or "", "Authorization": f"Bearer {SERVER_KEY or ''}"}
DOMAINS = tuple(domain.value for domain in DiagnosticDomain)
BASE_SEQUENCE = ("P01", "L01", "M01", "S01", "T01", "P02", "L02", "M02", "S02", "T02")
LONG_SEQUENCE = BASE_SEQUENCE + ("P03", "L03", "M03", "S03", "T03", "P04")


@dataclass
class LocalFixtures:
    users: tuple[str, str, str, str]
    tokens: tuple[str, str, str, str]
    profiles: tuple[str, str, str, str]
    university_a: str
    university_b: str
    plan_a: str
    plan_b: str


def _request(client: httpx.Client, method: str, path: str, *, ok: bool = True, **kwargs):
    response = client.request(method, f"{URL}{path}", timeout=10, **kwargs)
    if ok:
        assert response.status_code < 400, f"{method} {path}: {response.status_code} {response.text}"
    return response


def _post_row(client: httpx.Client, table: str, payload: dict) -> dict:
    return _request(client, "POST", f"/rest/v1/{table}", headers={**ADMIN, "Prefer": "return=representation"},
                    json=payload).json()[0]


def _rows(client: httpx.Client, table: str, **params) -> list[dict]:
    return _request(client, "GET", f"/rest/v1/{table}", headers=ADMIN,
                    params={"select": "*", **params}).json()


@pytest.fixture(scope="module")
def local_fixtures() -> LocalFixtures:
    suffix = uuid.uuid4().hex
    password = f"Local-{uuid.uuid4()}-Aa1!"
    user_ids: list[str] = []
    tokens: list[str] = []
    created: dict[str, list[str]] = {name: [] for name in ("study_plans", "majors", "faculties", "universities")}
    with httpx.Client() as client:
        try:
            for label in ("a1", "a2", "b1", "plan12"):
                email = f"diagnostic-{label}-{suffix}@local.test"
                user = _request(client, "POST", "/auth/v1/admin/users", headers=ADMIN,
                                json={"email": email, "password": password, "email_confirm": True}).json()
                user_ids.append(user["id"])
                signed = _request(client, "POST", "/auth/v1/token", params={"grant_type": "password"},
                                  headers={"apikey": ANON_KEY or ""},
                                  json={"email": email, "password": password}).json()
                tokens.append(signed["access_token"])

            universities = []
            plans = []
            for label in ("A", "B"):
                university = _post_row(client, "universities", {
                    "name_ar": f"جامعة اختبار {label} {suffix}", "name_en": f"Local Test {label} {suffix}",
                    "country": "LOCAL_ONLY"})
                universities.append(university["id"]); created["universities"].append(university["id"])
                faculty = _post_row(client, "faculties", {
                    "university_id": university["id"], "name_ar": f"كلية {label} {suffix}"})
                created["faculties"].append(faculty["id"])
                major = _post_row(client, "majors", {
                    "faculty_id": faculty["id"], "name_ar": f"تخصص {label} {suffix}"})
                created["majors"].append(major["id"])
                plan = _post_row(client, "study_plans", {
                    "major_id": major["id"], "plan_number": f"LOCAL-{label}-{suffix}",
                    "total_credit_hours": 0, "status": "draft"})
                plans.append(plan["id"]); created["study_plans"].append(plan["id"])

            profile_ids = []
            for owner, plan in zip(user_ids[:3], (plans[0], plans[0], plans[1])):
                profile_ids.append(_post_row(client, "student_academic_profiles", {
                    "owner_user_id": owner, "study_plan_id": plan})["id"])
            profile_ids.append(_post_row(client, "student_academic_profiles", {
                "owner_user_id": user_ids[3], "study_plan_id": PLAN12})["id"])
            yield LocalFixtures(tuple(user_ids), tuple(tokens), tuple(profile_ids),
                                universities[0], universities[1], plans[0], plans[1])
        finally:
            for user_id in user_ids:
                _request(client, "DELETE", f"/auth/v1/admin/users/{user_id}", headers=ADMIN, ok=False)
            for table in ("study_plans", "majors", "faculties", "universities"):
                for row_id in reversed(created[table]):
                    _request(client, "DELETE", f"/rest/v1/{table}", headers=ADMIN,
                             params={"id": f"eq.{row_id}"}, ok=False)


def _session_payload(fx: LocalFixtures, *, owner=0, profile=0, institution=None, plan=None,
                     version: str | None = None, question="P01") -> dict:
    return {"owner_user_id": fx.users[owner], "profile_id": fx.profiles[profile],
            "institution_id": institution or fx.university_a, "study_plan_id": plan or fx.plan_a,
            "assessment_version": version or f"RUNTIME-{uuid.uuid4()}", "status": "IN_PROGRESS",
            "current_question_id": question}


def _create_session(client: httpx.Client, fx: LocalFixtures, **kwargs) -> dict:
    return _post_row(client, "student_diagnostic_sessions", _session_payload(fx, **kwargs))


def _rpc(client: httpx.Client, session: dict, question_id: str, *, next_question: str | None,
         results=None, owner: str | None = None, option="A", ok=True):
    question = QUESTIONS_BY_ID[question_id]
    return _request(client, "POST", "/rest/v1/rpc/record_student_diagnostic_answer",
        headers=ADMIN, ok=ok, json={"p_session_id": session["id"],
            "p_owner_user_id": owner or session["owner_user_id"], "p_question_id": question_id,
            "p_selected_option": option, "p_domain": question.domain.value,
            "p_difficulty": question.difficulty, "p_is_correct": option == question.correct_option,
            "p_next_question_id": next_question, "p_results": results})


def _valid_results(sequence: tuple[str, ...], option="A") -> list[dict]:
    answers = tuple(AnswerEvidence(qid, option, option == QUESTIONS_BY_ID[qid].correct_option)
                    for qid in sequence)
    return [{"domain": result.domain.value, "score": result.score,
             "confidence": result.confidence, "response_count": result.response_count,
             "reason_codes": list(result.reason_codes),
             "scoring_policy_version": "DIAGNOSTIC_SCORING_V1"}
            for result in (score_domain(domain, answers) for domain in DiagnosticDomain)]


def _advance(client: httpx.Client, session: dict, sequence: tuple[str, ...]) -> None:
    for current, next_question in zip(sequence, sequence[1:]):
        _rpc(client, session, current, next_question=next_question)


def _state(client: httpx.Client, session_id: str) -> tuple[dict, list[dict], list[dict]]:
    session = _rows(client, "student_diagnostic_sessions", id=f"eq.{session_id}")[0]
    responses = _rows(client, "student_diagnostic_responses", session_id=f"eq.{session_id}")
    results = _rows(client, "student_diagnostic_skill_results", session_id=f"eq.{session_id}")
    return session, sorted(responses, key=lambda row: row["response_order"]), sorted(
        results, key=lambda row: row["domain"])


def test_scope_trigger_and_browser_roles_are_closed(local_fixtures: LocalFixtures) -> None:
    fx = local_fixtures
    with httpx.Client() as client:
        valid = _create_session(client, fx)
        invalid = (
            _session_payload(fx, profile=1),
            _session_payload(fx, profile=2),
            _session_payload(fx, institution=fx.university_b),
            _session_payload(fx, plan=fx.plan_b),
            {**_session_payload(fx), "profile_id": str(uuid.uuid4())},
        )
        for payload in invalid:
            assert _request(client, "POST", "/rest/v1/student_diagnostic_sessions",
                            headers={**ADMIN, "Prefer": "return=representation"}, json=payload,
                            ok=False).status_code >= 400

        for token in fx.tokens[:3]:
            headers = {"apikey": ANON_KEY or "", "Authorization": f"Bearer {token}"}
            for table in ("student_diagnostic_sessions", "student_diagnostic_responses",
                          "student_diagnostic_skill_results"):
                assert _request(client, "GET", f"/rest/v1/{table}", headers=headers,
                                params={"select": "*"}, ok=False).status_code in (401, 403)
                for method in ("POST", "PATCH", "DELETE"):
                    assert _request(client, method, f"/rest/v1/{table}", headers=headers,
                                    params={"id": f"eq.{valid['id']}"},
                                    json={} if method != "DELETE" else None, ok=False).status_code in (401, 403)
            assert _request(client, "POST", "/rest/v1/rpc/record_student_diagnostic_answer",
                            headers=headers, json={}, ok=False).status_code in (401, 403, 404)
        abandoned = _request(client, "PATCH", "/rest/v1/student_diagnostic_sessions",
                             headers={**ADMIN, "Prefer": "return=representation"},
                             params={"id": f"eq.{valid['id']}"},
                             json={"status": "ABANDONED", "current_question_id": None})
        assert abandoned.json()[0]["status"] == "ABANDONED"


def test_question_boundaries_replays_forgery_and_atomic_rollback(local_fixtures: LocalFixtures) -> None:
    fx = local_fixtures
    with httpx.Client() as client:
        nine = _create_session(client, fx, question=BASE_SEQUENCE[0])
        _advance(client, nine, BASE_SEQUENCE[:9])
        before = _state(client, nine["id"])
        rejected = _rpc(client, nine, BASE_SEQUENCE[8], next_question=None,
                        results=_valid_results(BASE_SEQUENCE[:9]), ok=False)
        assert rejected.status_code >= 400 and _state(client, nine["id"]) == before

        ten = _create_session(client, fx, question=BASE_SEQUENCE[0])
        _advance(client, ten, BASE_SEQUENCE)
        completed = _rpc(client, ten, BASE_SEQUENCE[-1], next_question=None,
                         results=_valid_results(BASE_SEQUENCE))
        assert completed.json()["status"] == "COMPLETED"
        state, responses, results = _state(client, ten["id"])
        assert state["question_count"] == 10 and len(responses) == 10 and len(results) == 5

        sixteen = _create_session(client, fx, question=LONG_SEQUENCE[0])
        _advance(client, sixteen, LONG_SEQUENCE)
        at_fifteen = _state(client, sixteen["id"])
        assert at_fifteen[0]["question_count"] == 15
        forced = _rpc(client, sixteen, LONG_SEQUENCE[-1], next_question="P05", ok=False)
        assert forced.status_code >= 400 and _state(client, sixteen["id"]) == at_fifteen
        _rpc(client, sixteen, LONG_SEQUENCE[-1], next_question=None,
             results=_valid_results(LONG_SEQUENCE))
        assert _state(client, sixteen["id"])[0]["question_count"] == 16
        assert _rpc(client, sixteen, LONG_SEQUENCE[-1], next_question=None,
                    results=_valid_results(LONG_SEQUENCE), ok=False).status_code >= 400

        replay = _create_session(client, fx, question="P01")
        _rpc(client, replay, "P01", next_question="L01")
        snapshot = _state(client, replay["id"])
        for current, nxt in (("P01", "M01"), ("L01", "P01"), ("L01", "L01")):
            assert _rpc(client, replay, current, next_question=nxt, ok=False).status_code >= 400
            assert _state(client, replay["id"]) == snapshot

        mutations = []
        valid_results = _valid_results(BASE_SEQUENCE)
        mutations.append(valid_results[:4])
        mutations.append(valid_results + [deepcopy(valid_results[0])])
        duplicate = deepcopy(valid_results); duplicate[1]["domain"] = duplicate[0]["domain"]; mutations.append(duplicate)
        for field, value in (("domain", "FORGED"), ("score", -1), ("score", 101),
                             ("confidence", "CERTAIN"), ("response_count", 5),
                             ("scoring_policy_version", "FORGED_V1")):
            item = deepcopy(valid_results); item[0][field] = value; mutations.append(item)
        for reasons in (None, ["ARBITRARY", "RESPONSES_2"],
                        ["MODELED_DIAGNOSTIC_BASELINE", "MODELED_DIAGNOSTIC_BASELINE"],
                        ["RESPONSES_2", "LIMITED_ITEM_COUNT"],
                        ["MODELED_DIAGNOSTIC_BASELINE", "RESPONSES_5"]):
            item = deepcopy(valid_results)
            if reasons is None: item[0].pop("reason_codes")
            else: item[0]["reason_codes"] = reasons
            mutations.append(item)

        for malformed in mutations:
            session = _create_session(client, fx, question=BASE_SEQUENCE[0])
            _advance(client, session, BASE_SEQUENCE)
            before = _state(client, session["id"])
            assert _rpc(client, session, BASE_SEQUENCE[-1], next_question=None,
                        results=malformed, ok=False).status_code >= 400
            assert _state(client, session["id"]) == before


def _services(client: httpx.AsyncClient, policies: GradePolicyRegistry | None = None):
    catalog = SupabaseAcademicCatalogRepository(URL or "", SERVER_KEY or "", client)
    students_repo = SupabaseStudentAcademicRepository(URL or "", SERVER_KEY or "", client)
    diagnostics_repo = SupabaseDiagnosticRepository(URL or "", SERVER_KEY or "", client)
    students = StudentService(students_repo, EligibilityService(catalog), catalog,
                              grade_policies=policies, diagnostic_repository=diagnostics_repo)
    return students, DiagnosticService(diagnostics_repo, students), diagnostics_repo


async def _complete(service: DiagnosticService, owner: str) -> dict:
    payload = await service.start(owner)
    while payload["status"] == "IN_PROGRESS":
        question = payload["question"]
        assert question is not None
        bank_item = QUESTIONS_BY_ID[question["question_id"]]
        payload = await service.answer(owner, payload["session_id"], bank_item.question_id,
                                       bank_item.correct_option)
    return payload


def test_real_service_happy_path_concurrency_and_intelligence(local_fixtures: LocalFixtures) -> None:
    fx = local_fixtures

    async def scenario() -> None:
        async with httpx.AsyncClient(timeout=20) as client:
            students, diagnostics, repo = _services(client)

            cold = await students.get_student_intelligence_v2(fx.users[0])
            assert cold.cold_start_status == "COLD_START_NO_PERFORMANCE_EVIDENCE"
            assert cold.diagnostic_recommended is True and cold.skills == ()

            completed = await _complete(diagnostics, fx.users[0])
            assert completed["status"] == "COMPLETED"
            assert 10 <= completed["answered_count"] <= 16
            assert completed["answered_count"] == 12
            assert completed["question"] is None and len(completed["results"]) == 5
            serialized = str(completed)
            assert all(hidden not in serialized for hidden in ("correct_option", "is_correct", "difficulty_weight"))
            modeled = await students.get_student_intelligence_v2(fx.users[0])
            assert modeled.diagnostic_completed is True
            assert modeled.diagnostic_recommended is False
            assert modeled.skills and all(row.score is not None for row in modeled.skills)

            starts = await asyncio.gather(diagnostics.start(fx.users[1]), diagnostics.start(fx.users[1]))
            assert starts[0]["session_id"] == starts[1]["session_id"]
            active = await repo.load_active(fx.users[1], fx.plan_a, ASSESSMENT_VERSION)
            assert active is not None
            first = str(active["current_question_id"])
            answer = QUESTIONS_BY_ID[first].correct_option
            outcomes = await asyncio.gather(
                diagnostics.answer(fx.users[1], active["id"], first, answer),
                diagnostics.answer(fx.users[1], active["id"], first, answer),
                return_exceptions=True,
            )
            assert sum(isinstance(item, DiagnosticConflict) for item in outcomes) == 1
            advanced = await repo.load_session(fx.users[1], active["id"])
            assert advanced is not None and advanced["question_count"] == 1
            assert len(await repo.load_responses(active["id"])) == 1
            await diagnostics.abandon(fx.users[1], active["id"])

            final = await diagnostics.start(fx.users[1])
            while final["answered_count"] < 11:
                question = final["question"]
                bank_item = QUESTIONS_BY_ID[question["question_id"]]
                final = await diagnostics.answer(fx.users[1], final["session_id"],
                                                 bank_item.question_id, bank_item.correct_option)
            final_question = final["question"]
            bank_item = QUESTIONS_BY_ID[final_question["question_id"]]
            outcomes = await asyncio.gather(
                diagnostics.answer(fx.users[1], final["session_id"], bank_item.question_id,
                                   bank_item.correct_option),
                diagnostics.answer(fx.users[1], final["session_id"], bank_item.question_id,
                                   bank_item.correct_option),
                return_exceptions=True,
            )
            assert sum(isinstance(item, DiagnosticConflict) for item in outcomes) == 1
            closed = await repo.load_session(fx.users[1], final["session_id"])
            assert closed is not None and closed["status"] == "COMPLETED" and closed["question_count"] == 12
            _, result_rows = await repo.latest_completed(fx.users[1], fx.plan_a, ASSESSMENT_VERSION)
            assert len(result_rows) == 5 and len(await repo.load_responses(final["session_id"])) == 12

    asyncio.run(scenario())


def test_abandonment_and_completed_evidence_are_immutable(local_fixtures: LocalFixtures) -> None:
    fx = local_fixtures
    with httpx.Client() as client:
        session = _create_session(client, fx, owner=2, profile=2, institution=fx.university_b,
                                  plan=fx.plan_b, question="P01")
        _rpc(client, session, "P01", next_question="L01")
        abandoned = _request(client, "PATCH", "/rest/v1/student_diagnostic_sessions",
            headers={**ADMIN, "Prefer": "return=representation"}, params={"id": f"eq.{session['id']}"},
            json={"status": "ABANDONED", "current_question_id": None}).json()[0]
        assert abandoned["completed_at"] is None
        assert _rpc(client, abandoned, "L01", next_question="M01", ok=False).status_code >= 400
        assert _request(client, "PATCH", "/rest/v1/student_diagnostic_sessions", headers=ADMIN,
                        params={"id": f"eq.{session['id']}"},
                        json={"status": "IN_PROGRESS", "current_question_id": "L01"},
                        ok=False).status_code >= 400
        replacement = _create_session(client, fx, owner=2, profile=2, institution=fx.university_b,
                                      plan=fx.plan_b, version=abandoned["assessment_version"])
        assert replacement["status"] == "IN_PROGRESS"

        completed_rows = _rows(client, "student_diagnostic_sessions", status="eq.COMPLETED", limit="1")
        assert completed_rows
        completed = completed_rows[0]
        original = _state(client, completed["id"])
        session_changes = ({"status": "ABANDONED"}, {"question_count": 1},
                           {"owner_user_id": fx.users[2]}, {"profile_id": fx.profiles[2]},
                           {"study_plan_id": fx.plan_b}, {"institution_id": fx.university_b},
                           {"started_at": "2020-01-01T00:00:00Z"},
                           {"completed_at": "2020-01-01T00:00:00Z"})
        for change in session_changes:
            assert _request(client, "PATCH", "/rest/v1/student_diagnostic_sessions", headers=ADMIN,
                            params={"id": f"eq.{completed['id']}"}, json=change,
                            ok=False).status_code >= 400
        response = original[1][0]; result = original[2][0]
        child_ops = (
            ("POST", "student_diagnostic_responses", {k: v for k, v in response.items() if k != "id"}),
            ("PATCH", "student_diagnostic_responses", {"selected_option": "D"}),
            ("DELETE", "student_diagnostic_responses", None),
            ("POST", "student_diagnostic_skill_results", {k: v for k, v in result.items() if k != "id"}),
            ("PATCH", "student_diagnostic_skill_results", {"score": 1}),
            ("DELETE", "student_diagnostic_skill_results", None),
        )
        for method, table, body in child_ops:
            target = response["id"] if "responses" in table else result["id"]
            assert _request(client, method, f"/rest/v1/{table}", headers=ADMIN,
                            params={"id": f"eq.{target}"}, json=body, ok=False).status_code >= 400
        assert _state(client, completed["id"]) == original


def test_v2_grade_policy_preference_and_eligibility_invariants(local_fixtures: LocalFixtures) -> None:
    fx = local_fixtures

    async def scenario() -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            students, diagnostics, _ = _services(client)
            before = await students.get_course_recommendations(fx.users[3])
            before_codes = {row.course_code for row in before.ranked_recommendations}
            completed = await _complete(diagnostics, fx.users[3])
            assert completed["status"] == "COMPLETED"
            after = await students.get_course_recommendations(fx.users[3])
            assert {row.course_code for row in after.ranked_recommendations} == before_codes

            await students.create_attempt(
                fx.users[3], "1501110", AttemptOutcome.PASSED, raw_numeric_grade=Decimal("95"),
                attempt_sequence=1, record_source="university_integration",
                performance_provenance=PerformanceProvenance.OFFICIAL_VERIFIED,
                performance_verification_state=PerformanceVerificationState.VERIFIED,
                performance_source_reference=grading_policy_source_reference(
                    "10000000-0000-0000-0000-000000000001",
                    "FAKE_UNIVERSITY_GRADING_POLICY_V1"),
            )
            fail_closed = await students.get_student_intelligence_v2(fx.users[3])
            assert fail_closed.verified_grade_count == 0
            assert any("official_grade_mastery=UNAVAILABLE_UNVERIFIED_POLICY" in item
                       for item in fail_closed.limitations)

            institution = await students.resolve_student_university_id(fx.users[3])
            policy = FAKE_UNIVERSITY_GRADING_POLICY_V1
            assert policy.institution_id == institution and policy.study_plan_id == PLAN12
            governed_students, _, governed_repo = _services(client, GradePolicyRegistry((policy,)))
            governed = await governed_students.get_student_intelligence_v2(fx.users[3])
            assert governed.verified_grade_count == 1
            assert any("OFFICIAL_EVIDENCE_DOMINANT" in row.reason_codes for row in governed.skills)

            state = await governed_students.get_profile(fx.users[3])
            records = await governed_students.list_attempts(fx.users[3])
            session, rows = await governed_repo.latest_completed(fx.users[3], PLAN12 or "", ASSESSMENT_VERSION)
            assert session is not None
            from datetime import datetime
            from app.student_intelligence.diagnostic import DiagnosticDomainResult
            diagnostic_rows = tuple(DiagnosticDomainResult(
                DiagnosticDomain(row["domain"]), int(row["score"]), row["confidence"],
                int(row["response_count"]), tuple(row["reason_codes"])) for row in rows)
            base = build_student_intelligence_profile_v2(
                state, institution, records, policy, diagnostic_results=diagnostic_rows,
                diagnostic_version=ASSESSMENT_VERSION,
                diagnostic_completed_at=datetime.fromisoformat(session["completed_at"].replace("Z", "+00:00")))
            stated = build_student_intelligence_profile_v2(
                state, institution, records, policy, diagnostic_results=diagnostic_rows,
                diagnostic_version=ASSESSMENT_VERSION,
                diagnostic_completed_at=datetime.fromisoformat(session["completed_at"].replace("Z", "+00:00")),
                preferences={"statement": "I am great at math"})
            assert {row.skill_id: row.score for row in base.skills} == {
                row.skill_id: row.score for row in stated.skills}

    asyncio.run(scenario())


def test_actual_fastapi_routes_are_owner_scoped_and_hide_answer_keys(local_fixtures: LocalFixtures) -> None:
    from app.main import app

    fx = local_fixtures
    auth = [{"Authorization": f"Bearer {token}"} for token in fx.tokens[:3]]
    with httpx.Client() as raw:
        prior_completed = _rows(raw, "student_diagnostic_sessions",
                                owner_user_id=f"eq.{fx.users[0]}", status="eq.COMPLETED")
    assert prior_completed
    completed_id = prior_completed[0]["id"]
    with TestClient(app) as client:
        intelligence = client.get("/api/v1/me/student-intelligence", headers=auth[0])
        assert intelligence.status_code == 200
        status = client.get("/api/v1/me/diagnostic/status", headers=auth[0])
        assert status.status_code == 200
        started = client.post("/api/v1/me/diagnostic/start", headers=auth[0])
        assert started.status_code == 200
        body = started.json(); session_id = body["session_id"]
        assert body["question"] is not None
        assert not ({"correct_option", "is_correct", "answer_key", "weight"} & set(body["question"]))
        assert client.get(f"/api/v1/me/diagnostic/{session_id}/next", headers=auth[0]).status_code == 200
        for foreign in auth[1:]:
            assert client.get(f"/api/v1/me/diagnostic/{session_id}/next", headers=foreign).status_code == 404
            assert client.post(f"/api/v1/me/diagnostic/{session_id}/answer", headers=foreign,
                               json={"question_id": body["question"]["question_id"],
                                     "selected_option": "A"}).status_code == 404
            assert client.post(f"/api/v1/me/diagnostic/{session_id}/abandon", headers=foreign).status_code == 404
        random_id = str(uuid.uuid4())
        assert client.get(f"/api/v1/me/diagnostic/{random_id}/next", headers=auth[0]).status_code == 404
        assert client.get(f"/api/v1/me/diagnostic/{completed_id}/next", headers=auth[0]).status_code == 200
        assert client.post(f"/api/v1/me/diagnostic/{completed_id}/answer", headers=auth[0],
                           json={"question_id": "P01", "selected_option": "A"}).status_code == 409
        for foreign in auth[1:]:
            assert client.get(f"/api/v1/me/diagnostic/{completed_id}/next", headers=foreign).status_code == 404
        answered = client.post(f"/api/v1/me/diagnostic/{session_id}/answer", headers=auth[0],
                               json={"question_id": body["question"]["question_id"],
                                     "selected_option": "A"})
        assert answered.status_code == 200
        assert client.post(f"/api/v1/me/diagnostic/{session_id}/abandon", headers=auth[0]).status_code == 204
        assert client.get(f"/api/v1/me/diagnostic/{session_id}/next", headers=auth[0]).status_code == 200
        for foreign in auth[1:]:
            assert client.get(f"/api/v1/me/diagnostic/{session_id}/next", headers=foreign).status_code == 404
        assert client.post(f"/api/v1/me/diagnostic/{session_id}/answer", headers=auth[0],
                           json={"question_id": answered.json()["question"]["question_id"],
                                 "selected_option": "A"}).status_code == 409
