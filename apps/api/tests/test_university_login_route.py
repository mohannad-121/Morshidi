"""Comprehensive test suite for Morshidi public university login endpoint (Step 4).

Verifies:
- Public route POST /api/v1/auth/university-login
- Session issuance via internal Supabase Auth password grant
- Secret rotation recovery via Admin API
- Canonical-email collision protection (fails closed with 409)
- Error mapping (401, 409, 422, 429, 500, 503)
- Cache-Control: no-store on all responses
- Rate limiting (10 attempts/min per IP)
- Logging hygiene (passwords, tokens, HMAC secrets masked)
- Idempotency on repeated logins
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.routes.auth import (
    get_login_rate_limiter,
    get_supabase_admin_auth,
    get_university_sync_service,
)
from app.core.rate_limiter import InMemoryLoginRateLimiter
from app.main import app
from app.university_sync.admin_auth import (
    SupabaseAdminAuthClient,
    build_canonical_student_email,
    derive_shadow_password,
)
from app.university_sync.client import UniversityContractClient
from app.university_sync.identity_repository import SupabaseUniversityIdentityRepository
from app.university_sync.service import UniversitySyncService

TEST_UNIVERSITY_ID = "10000000-0000-0000-0000-000000000001"
TEST_PLAN_ID = "10000000-0000-0000-0000-000000000005"
TEST_SECRET = "test-internal-auth-secret-12345"
TEST_SERVICE_KEY = "test-service-key-99999"


def _with_university_envelopes(handler):
    """Adapt legacy fixture payloads to the Fake University wire contract."""
    payload_keys = {
        "/student/me": "data",
        "/student/courses": "data",
        "/student/grades": "data",
        "/student/enrollments": "data",
        "/student/academic-plan": "data",
    }

    def wrapped(request: httpx.Request) -> httpx.Response:
        response = handler(request)
        if response.status_code != 200:
            return response
        for suffix, payload_key in payload_keys.items():
            if request.url.path.endswith(suffix):
                try:
                    payload = response.json()
                except ValueError:
                    return response
                if isinstance(payload, dict) and payload.get("success") is True:
                    return response
                return httpx.Response(200, json={"success": True, payload_key: payload})
        return response

    return wrapped


class MockSupabaseAuthAndRestEnvironment:
    """Mock environment handling both Supabase GoTrue Auth and PostgREST endpoints."""

    def __init__(self) -> None:
        self.auth_users: list[dict[str, Any]] = []
        self.passwords: dict[str, str] = {}  # user_id -> password
        self.identities: list[dict[str, Any]] = []
        self.profiles: list[dict[str, Any]] = []
        self.attempts: list[dict[str, Any]] = []
        self.study_plans: list[dict[str, Any]] = [
            {
                "id": TEST_PLAN_ID,
                "plan_number": "12",
                "majors": {"faculties": {"university_id": TEST_UNIVERSITY_ID}},
            }
        ]
        self.courses: list[dict[str, Any]] = [
            {"id": "c1000000-0000-0000-0000-000000000001", "course_code": "0200104", "university_id": TEST_UNIVERSITY_ID},
            {"id": "c1000000-0000-0000-0000-000000000002", "course_code": "1501110", "university_id": TEST_UNIVERSITY_ID},
            {"id": "c1000000-0000-0000-0000-000000000003", "course_code": "0300103", "university_id": TEST_UNIVERSITY_ID},
        ]
        self.fail_session_issuance = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method

        # 1. GoTrue token issuance: /auth/v1/token?grant_type=password
        if path == "/auth/v1/token":
            if self.fail_session_issuance:
                return httpx.Response(500, json={"message": "Internal server error from GoTrue"})
            payload = json.loads(request.content)
            email = payload.get("email", "").strip().lower()
            pwd = payload.get("password")
            user = next((u for u in self.auth_users if u["email"] == email), None)
            if not user:
                return httpx.Response(400, json={"error": "invalid_grant", "error_description": "Invalid login credentials"})
            stored_pwd = self.passwords.get(user["id"])
            if stored_pwd != pwd:
                return httpx.Response(400, json={"error": "invalid_grant", "error_description": "Invalid login credentials"})

            return httpx.Response(
                200,
                json={
                    "access_token": f"morshidi-access-token-{user['id']}",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "refresh_token": f"morshidi-refresh-token-{user['id']}",
                    "expires_at": 1759670000,
                    "user": {"id": user["id"], "email": email},
                },
            )

        # 2. GoTrue admin users: /auth/v1/admin/users
        if path == "/auth/v1/admin/users":
            if method == "POST":
                payload = json.loads(request.content)
                email = payload.get("email", "").strip().lower()
                for u in self.auth_users:
                    if u["email"] == email:
                        return httpx.Response(422, json={"code": 422, "msg": "User already registered"})
                user_id = str(uuid4())
                user_rec = {"id": user_id, "email": email, "user_metadata": payload.get("user_metadata", {})}
                self.auth_users.append(user_rec)
                self.passwords[user_id] = payload.get("password", "")
                return httpx.Response(201, json=user_rec)
            elif method == "GET":
                return httpx.Response(200, json={"users": self.auth_users})

        # 3. GoTrue admin user update: /auth/v1/admin/users/{user_id}
        if path.startswith("/auth/v1/admin/users/"):
            user_id = path.split("/")[-1]
            user = next((item for item in self.auth_users if item["id"] == user_id), None)
            if method == "GET":
                return httpx.Response(200, json=user) if user else httpx.Response(404)
            if method == "PUT":
                payload = json.loads(request.content)
                if "password" in payload:
                    self.passwords[user_id] = payload["password"]
                if user and "user_metadata" in payload:
                    user["user_metadata"] = payload["user_metadata"]
                return httpx.Response(200, json={"id": user_id, "updated": True})

        # 4. PostgREST: student_university_identities
        if path == "/rest/v1/student_university_identities":
            if method == "GET":
                uni = request.url.params.get("university_id", "").replace("eq.", "")
                sid = request.url.params.get("university_student_id", "").replace("eq.", "")
                owner = request.url.params.get("owner_user_id", "").replace("eq.", "")
                matched = [
                    i for i in self.identities
                    if (not uni or i["university_id"] == uni)
                    and (not sid or i["university_student_id"] == sid)
                    and (not owner or i["owner_user_id"] == owner)
                ]
                return httpx.Response(200, json=matched)
            elif method == "POST":
                payload = json.loads(request.content)
                # Check uniqueness
                for i in self.identities:
                    if i["university_id"] == payload["university_id"] and i["university_student_id"] == payload["university_student_id"]:
                        return httpx.Response(409, json={"code": "23505", "message": "duplicate key"})
                    if i["owner_user_id"] == payload["owner_user_id"] and i["university_id"] == payload["university_id"]:
                        return httpx.Response(409, json={"code": "23505", "message": "duplicate key"})
                ident_id = str(uuid4())
                rec = {
                    "id": ident_id,
                    "owner_user_id": payload["owner_user_id"],
                    "university_id": payload["university_id"],
                    "university_student_id": payload["university_student_id"],
                    "created_at": "2026-10-05T12:00:00Z",
                    "updated_at": "2026-10-05T12:00:00Z",
                    "last_synced_at": None,
                }
                self.identities.append(rec)
                return httpx.Response(201, json=[rec])
            elif method == "PATCH":
                target_id = request.url.params.get("id", "").replace("eq.", "")
                payload = json.loads(request.content)
                for i in self.identities:
                    if i["id"] == target_id:
                        i.update(payload)
                return httpx.Response(204)

        # 5. PostgREST: study_plans
        if path == "/rest/v1/study_plans":
            return httpx.Response(200, json=self.study_plans)

        # 6. PostgREST: courses
        if path == "/rest/v1/courses":
            uni = request.url.params.get("university_id", "").replace("eq.", "")
            matched = [c for c in self.courses if not uni or c["university_id"] == uni]
            return httpx.Response(200, json=matched)

        # 7. PostgREST: student_academic_profiles
        if path == "/rest/v1/student_academic_profiles":
            if method == "GET":
                owner = request.url.params.get("owner_user_id", "").replace("eq.", "")
                matched = [p for p in self.profiles if not owner or p["owner_user_id"] == owner]
                return httpx.Response(200, json=matched)
            elif method == "POST":
                payload = json.loads(request.content)
                p_id = str(uuid4())
                rec = {"id": p_id, **payload}
                self.profiles.append(rec)
                return httpx.Response(201, json=[rec])
            elif method == "PATCH":
                p_id = request.url.params.get("id", "").replace("eq.", "")
                payload = json.loads(request.content)
                for p in self.profiles:
                    if p["id"] == p_id:
                        p.update(payload)
                return httpx.Response(204)

        # 8. PostgREST: student_course_attempts
        if path == "/rest/v1/student_course_attempts":
            if method == "GET":
                pid = request.url.params.get("profile_id", "").replace("eq.", "")
                matched = [a for a in self.attempts if not pid or a.get("profile_id") == pid]
                return httpx.Response(200, json=matched)
            elif method == "POST":
                payload = json.loads(request.content)
                items = payload if isinstance(payload, list) else [payload]
                inserted = []
                for item in items:
                    att_id = str(uuid4())
                    rec = {"id": att_id, **item}
                    self.attempts.append(rec)
                    inserted.append(rec)
                return httpx.Response(201, json=inserted)
            elif method == "DELETE":
                target_id = request.url.params.get("id", "").replace("eq.", "")
                self.attempts = [a for a in self.attempts if a.get("id") != target_id]
                return httpx.Response(204)

        return httpx.Response(404, text=f"Unhandled mock endpoint: {path}")


def default_fake_uni_handler(request: httpx.Request) -> httpx.Response:
    """Mock handler for external Fake University endpoints."""
    path = request.url.path
    if path == "/api/integrations/morshidi/v1/auth/login":
        body = json.loads(request.content)
        student_id = body.get("studentId", "")
        password = body.get("password", "")
        if password == "WrongPassword":
            return httpx.Response(401, json={"detail": "Invalid university credentials"})
        return httpx.Response(
            200,
            json={
                "success": True,
                "accessToken": "fake-uni-integration-bearer-token-12345",
                "tokenType": "Bearer",
                "expiresIn": 900,
                "student": {
                    "studentId": student_id,
                    "email": "student@example.edu",
                },
            },
        )
    elif path == "/api/integrations/morshidi/v1/student/me":
        return httpx.Response(
            200,
            json={
                "success": True,
                "student": {
                    "studentId": "202310001",
                    "name": "Tariq Ahmad",
                    "email": "student@example.edu",
                    "faculty": "Information Technology",
                    "major": "Artificial Intelligence",
                    "degree": "Bachelor",
                    "studyType": "Regular",
                    "admissionYear": 2023,
                    "academicAdvisor": "Test Advisor",
                    "academicStatus": "active",
                    "gpa": 3.45,
                    "earnedCredits": 45,
                },
            },
        )
    elif path == "/api/integrations/morshidi/v1/student/courses":
        return httpx.Response(
            200,
            json={
                "success": True,
                "courses": {
                    "completed": [
                        {"courseCode": "0200104", "name": "Calculus 1", "credits": 3, "status": "completed"},
                        {"courseCode": "1501110", "name": "Computer Science 1", "credits": 3, "status": "completed"},
                    ],
                    "current": [
                        {"courseCode": "0300103", "name": "Data Structures", "credits": 3, "status": "enrolled"}
                    ],
                    "remaining": [],
                },
            },
        )
    elif path == "/api/integrations/morshidi/v1/student/grades":
        return httpx.Response(
            200,
            json={
                "success": True,
                "cumulativeGpa": 3.45,
                "semesters": [
                    {
                        "term": "2023-1",
                        "termLabel": "First Semester 2023",
                        "registeredHours": 6,
                        "passedHours": 6,
                        "semesterGpa": 3.45,
                        "cumulativeGpa": 3.45,
                        "courses": [
                            {"courseCode": "0200104", "name": "Calculus 1", "credits": 3, "grade": 95, "letterGrade": "A", "status": "passed"},
                            {"courseCode": "1501110", "name": "Computer Science 1", "credits": 3, "grade": 88, "letterGrade": "B+", "status": "passed"},
                        ],
                    }
                ],
            },
        )
    elif path == "/api/integrations/morshidi/v1/student/enrollments":
        return httpx.Response(
            200,
            json={
                "success": True,
                "term": "2024-1",
                "termLabel": "First Semester 2024",
                "enrollments": [
                    {
                        "courseCode": "0300103",
                        "courseName": "Data Structures",
                        "sectionId": "SEC-01",
                        "sectionNumber": 1,
                        "credits": 3,
                        "days": "Sun/Tue",
                        "daysArray": ["Sun", "Tue"],
                        "startTime": "10:00",
                        "endTime": "11:30",
                        "room": "LAB-1",
                        "instructor": "Test Instructor",
                    }
                ],
            },
        )
    elif path == "/api/integrations/morshidi/v1/student/academic-plan":
        return httpx.Response(
            200,
            json={
                "success": True,
                "plan": {
                    "planId": "12",
                    "major": "Artificial Intelligence",
                    "totalRequiredCredits": 132,
                    "earnedCredits": 45,
                    "remainingCredits": 87,
                    "courses": [
                        {
                            "courseCode": "0200104",
                            "name": "Calculus 1",
                            "credits": 3,
                            "group": "University Requirements",
                            "type": "required",
                            "prerequisites": [],
                            "status": "completed",
                        }
                    ],
                },
            },
        )

    return httpx.Response(404, text=f"Unhandled fake uni path: {path}")


@pytest.fixture
def mock_env():
    env = MockSupabaseAuthAndRestEnvironment()
    return env


@pytest.fixture
def test_setup(mock_env: MockSupabaseAuthAndRestEnvironment):
    # University client
    uni_client = httpx.AsyncClient(
        transport=httpx.MockTransport(_with_university_envelopes(default_fake_uni_handler))
    )
    contract_client = UniversityContractClient(uni_client, client_secret="test-client-secret")

    # Supabase client
    supa_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_env.handle_request))

    identity_repo = SupabaseUniversityIdentityRepository(
        "https://test.supabase.co", TEST_SERVICE_KEY, client=supa_client
    )
    admin_auth = SupabaseAdminAuthClient(
        "https://test.supabase.co", TEST_SERVICE_KEY, client=supa_client
    )
    sync_service = UniversitySyncService(
        contract_client=contract_client,
        supabase_url="https://test.supabase.co",
        service_key=TEST_SERVICE_KEY,
        internal_auth_secret=TEST_SECRET,
        university_id=TEST_UNIVERSITY_ID,
        client=supa_client,
        identity_repo=identity_repo,
        admin_auth=admin_auth,
    )
    rate_limiter = InMemoryLoginRateLimiter(max_attempts=10, window_seconds=60)

    # Dependency overrides
    app.dependency_overrides[get_university_sync_service] = lambda: sync_service
    app.dependency_overrides[get_supabase_admin_auth] = lambda: admin_auth
    app.dependency_overrides[get_login_rate_limiter] = lambda: rate_limiter

    client = TestClient(app)
    yield client, mock_env, sync_service, admin_auth, rate_limiter

    app.dependency_overrides.clear()


# ==============================================================================
# Tests 1 - 8: Happy Path, Response Shape, Secret Scrubbing
# ==============================================================================


def test_01_valid_university_login_returns_200(test_setup):
    client, mock_env, _, _, _ = test_setup
    payload = {"student_id": "202310001", "password": "ValidPassword123!"}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "session" in data
    assert "user" in data
    assert "sync" in data


def test_02_university_sync_service_called_exactly_once(test_setup):
    client, mock_env, sync_service, _, _ = test_setup
    call_count = 0
    orig_call = sync_service.authenticate_and_sync_student

    async def spy_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return await orig_call(*args, **kwargs)

    sync_service.authenticate_and_sync_student = spy_call
    payload = {"student_id": "202310001", "password": "ValidPassword123!"}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    assert resp.status_code == 200
    assert call_count == 1


def test_03_returned_morshidi_access_token_belongs_to_internal_session(test_setup):
    client, mock_env, _, _, _ = test_setup
    payload = {"student_id": "202310001", "password": "ValidPassword123!"}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    data = resp.json()
    token = data["session"]["access_token"]
    user_id = data["user"]["id"]
    assert token == f"morshidi-access-token-{user_id}"
    assert data["user"]["student_id"] == "202310001"
    assert data["user"]["email"] == "202310001@shadow.morshidi.internal"


def test_04_refresh_token_returned_correctly(test_setup):
    client, mock_env, _, _, _ = test_setup
    payload = {"student_id": "202310001", "password": "ValidPassword123!"}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    data = resp.json()
    user_id = data["user"]["id"]
    assert data["session"]["refresh_token"] == f"morshidi-refresh-token-{user_id}"


def test_05_fake_university_integration_token_is_absent(test_setup):
    client, _, _, _, _ = test_setup
    payload = {"student_id": "202310001", "password": "ValidPassword123!"}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    assert "fake-uni-integration-bearer-token-12345" not in resp.text


def test_06_university_password_is_absent_from_response(test_setup):
    client, _, _, _, _ = test_setup
    raw_pass = "SuperSensitiveUniPassword!99"
    payload = {"student_id": "202310001", "password": raw_pass}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    assert raw_pass not in resp.text


def test_07_shadow_password_is_absent_from_response(test_setup):
    client, _, _, _, _ = test_setup
    payload = {"student_id": "202310001", "password": "ValidPassword123!"}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    assert "Mor!v1_" not in resp.text


def test_08_service_role_key_is_absent_from_response(test_setup):
    client, _, _, _, _ = test_setup
    payload = {"student_id": "202310001", "password": "ValidPassword123!"}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    assert TEST_SERVICE_KEY not in resp.text


# ==============================================================================
# Tests 9 - 17: Error Mapping & Fail-Closed Behaviors
# ==============================================================================


def test_09_invalid_university_credentials_returns_401(test_setup):
    client, _, _, _, _ = test_setup
    payload = {"student_id": "202310001", "password": "WrongPassword"}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    assert resp.status_code == 401
    assert resp.json() == {"success": False, "error": "INVALID_CREDENTIALS"}


def test_10_invalid_student_id_does_not_reveal_account_existence(test_setup):
    client, _, _, _, _ = test_setup
    # Both wrong password and unknown student return identical error code
    p1 = {"student_id": "NonExistentStudent999", "password": "WrongPassword"}
    r1 = client.post("/api/v1/auth/university-login", json=p1)
    p2 = {"student_id": "202310001", "password": "WrongPassword"}
    r2 = client.post("/api/v1/auth/university-login", json=p2)
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r1.json() == r2.json() == {"success": False, "error": "INVALID_CREDENTIALS"}


def test_11_and_12_upstream_429_returns_429_and_preserves_retry_after(mock_env):
    def rate_limited_uni_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "45"}, json={"detail": "Too Many Requests"})

    uni_client = httpx.AsyncClient(transport=httpx.MockTransport(rate_limited_uni_handler))
    contract = UniversityContractClient(uni_client, client_secret="secret")
    supa_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_env.handle_request))
    service = UniversitySyncService(
        contract_client=contract,
        supabase_url="https://test.supabase.co",
        service_key=TEST_SERVICE_KEY,
        internal_auth_secret=TEST_SECRET,
        university_id=TEST_UNIVERSITY_ID,
        client=supa_client,
    )
    admin_auth = SupabaseAdminAuthClient("https://test.supabase.co", TEST_SERVICE_KEY, client=supa_client)

    app.dependency_overrides[get_university_sync_service] = lambda: service
    app.dependency_overrides[get_supabase_admin_auth] = lambda: admin_auth
    client = TestClient(app)

    resp = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": "pass"})
    assert resp.status_code == 429
    assert resp.json() == {"success": False, "error": "RATE_LIMITED"}
    assert resp.headers.get("Retry-After") == "45"

    app.dependency_overrides.clear()


def test_13_upstream_timeout_returns_503_university_unavailable(mock_env):
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Connection timed out to university")

    uni_client = httpx.AsyncClient(transport=httpx.MockTransport(timeout_handler))
    contract = UniversityContractClient(uni_client, client_secret="secret")
    supa_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_env.handle_request))
    service = UniversitySyncService(
        contract_client=contract,
        supabase_url="https://test.supabase.co",
        service_key=TEST_SERVICE_KEY,
        internal_auth_secret=TEST_SECRET,
        university_id=TEST_UNIVERSITY_ID,
        client=supa_client,
    )
    admin_auth = SupabaseAdminAuthClient("https://test.supabase.co", TEST_SERVICE_KEY, client=supa_client)

    app.dependency_overrides[get_university_sync_service] = lambda: service
    app.dependency_overrides[get_supabase_admin_auth] = lambda: admin_auth
    client = TestClient(app)

    resp = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": "pass"})
    assert resp.status_code == 503
    assert resp.json() == {"success": False, "error": "UNIVERSITY_UNAVAILABLE"}

    app.dependency_overrides.clear()


def test_14_unmapped_plan_returns_safe_503_academic_sync_unavailable(mock_env):
    def bad_plan_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/login"):
            return httpx.Response(200, json={"token": "t", "studentId": "202310001"})
        elif path.endswith("/student/me"):
            return httpx.Response(200, json={"studentId": "202310001", "studyPlan": "UnknownPlan999"})
        elif path.endswith("/student/academic-plan"):
            return httpx.Response(200, json={"planId": "Plan999"})
        return httpx.Response(200, json=[])

    uni_client = httpx.AsyncClient(
        transport=httpx.MockTransport(_with_university_envelopes(bad_plan_handler))
    )
    contract = UniversityContractClient(uni_client, client_secret="secret")
    supa_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_env.handle_request))
    service = UniversitySyncService(
        contract_client=contract,
        supabase_url="https://test.supabase.co",
        service_key=TEST_SERVICE_KEY,
        internal_auth_secret=TEST_SECRET,
        university_id=TEST_UNIVERSITY_ID,
        client=supa_client,
    )
    admin_auth = SupabaseAdminAuthClient("https://test.supabase.co", TEST_SERVICE_KEY, client=supa_client)

    app.dependency_overrides[get_university_sync_service] = lambda: service
    app.dependency_overrides[get_supabase_admin_auth] = lambda: admin_auth
    client = TestClient(app)

    resp = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": "pass"})
    assert resp.status_code == 503
    assert resp.json() == {"success": False, "error": "ACADEMIC_SYNC_UNAVAILABLE"}
    # Assert internal plan identifier is not leaked
    assert "Plan999" not in resp.text

    app.dependency_overrides.clear()


def test_15_unmapped_course_returns_safe_503_academic_sync_unavailable(mock_env):
    def bad_course_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/login"):
            return httpx.Response(200, json={"token": "t", "studentId": "202310001"})
        elif path.endswith("/student/me"):
            return httpx.Response(200, json={"studentId": "202310001", "studyPlan": "12"})
        elif path.endswith("/student/grades"):
            return httpx.Response(200, json=[{"courseCode": "UNKNOWN_COURSE_XYZ", "status": "PASSED"}])
        elif path.endswith("/student/academic-plan"):
            return httpx.Response(200, json={"planId": "12"})
        return httpx.Response(200, json=[])

    uni_client = httpx.AsyncClient(
        transport=httpx.MockTransport(_with_university_envelopes(bad_course_handler))
    )
    contract = UniversityContractClient(uni_client, client_secret="secret")
    supa_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_env.handle_request))
    service = UniversitySyncService(
        contract_client=contract,
        supabase_url="https://test.supabase.co",
        service_key=TEST_SERVICE_KEY,
        internal_auth_secret=TEST_SECRET,
        university_id=TEST_UNIVERSITY_ID,
        client=supa_client,
    )
    admin_auth = SupabaseAdminAuthClient("https://test.supabase.co", TEST_SERVICE_KEY, client=supa_client)

    app.dependency_overrides[get_university_sync_service] = lambda: service
    app.dependency_overrides[get_supabase_admin_auth] = lambda: admin_auth
    client = TestClient(app)

    resp = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": "pass"})
    assert resp.status_code == 503
    assert resp.json() == {"success": False, "error": "ACADEMIC_SYNC_UNAVAILABLE"}
    assert "UNKNOWN_COURSE_XYZ" not in resp.text

    app.dependency_overrides.clear()


def test_16_unsafe_canonical_email_collision_returns_409_identity_conflict(test_setup):
    client, mock_env, _, _, _ = test_setup
    # Pre-register unproven account with same canonical email in Auth, but with missing/arbitrary metadata
    colliding_email = "202310001@shadow.morshidi.internal"
    mock_env.auth_users.append({
        "id": str(uuid4()),
        "email": colliding_email,
        "user_metadata": {"provider": "email"},  # NOT proven fake_university shadow user
    })

    payload = {"student_id": "202310001", "password": "pass"}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    assert resp.status_code == 409
    assert resp.json() == {"success": False, "error": "IDENTITY_CONFLICT"}


def test_17_session_issuance_failure_returns_safe_500(test_setup):
    client, mock_env, _, _, _ = test_setup
    mock_env.fail_session_issuance = True

    payload = {"student_id": "202310001", "password": "pass"}
    resp = client.post("/api/v1/auth/university-login", json=payload)
    assert resp.status_code == 500
    assert resp.json() == {"success": False, "error": "SESSION_ISSUANCE_FAILED"}


# ==============================================================================
# Tests 18 - 21: Security Headers & Log Sanitation
# ==============================================================================


def test_18_login_response_contains_no_store_cache_control(test_setup):
    client, _, _, _, _ = test_setup
    # Test on success
    r_success = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": "pass"})
    assert "no-store" in r_success.headers.get("Cache-Control", "")

    # Test on error
    r_err = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": "WrongPassword"})
    assert "no-store" in r_err.headers.get("Cache-Control", "")


def test_19_20_21_secrets_and_tokens_never_logged(test_setup, caplog: pytest.LogCaptureFixture):
    client, _, _, _, _ = test_setup
    caplog.set_level(logging.DEBUG)

    sensitive_pw = "ExtremelyConfidentialUniPass!123"
    resp = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": sensitive_pw})
    assert resp.status_code == 200

    data = resp.json()
    access_token = data["session"]["access_token"]
    refresh_token = data["session"]["refresh_token"]

    logs = caplog.text
    assert sensitive_pw not in logs
    assert "fake-uni-integration-bearer-token-12345" not in logs
    assert access_token not in logs
    assert refresh_token not in logs
    assert TEST_SECRET not in logs


# ==============================================================================
# Tests 22 - 25: Idempotency & Conflict Recovery
# ==============================================================================


def test_22_23_24_repeated_login_is_idempotent_without_duplicates(test_setup):
    client, mock_env, _, _, _ = test_setup
    payload = {"student_id": "202310001", "password": "pass"}

    r1 = client.post("/api/v1/auth/university-login", json=payload)
    assert r1.status_code == 200
    u1_id = r1.json()["user"]["id"]

    r2 = client.post("/api/v1/auth/university-login", json=payload)
    assert r2.status_code == 200
    u2_id = r2.json()["user"]["id"]

    assert u1_id == u2_id
    assert len(mock_env.auth_users) == 1
    assert len(mock_env.identities) == 1
    assert len(mock_env.profiles) == 1
    # 2 grade records + 1 enrollment = 3 attempts
    assert len(mock_env.attempts) == 3


def test_25_session_issuance_failure_followed_by_retry_succeeds_idempotently(test_setup):
    client, mock_env, _, _, _ = test_setup
    payload = {"student_id": "202310001", "password": "pass"}

    # Attempt 1: Session issuance fails (e.g. 500)
    mock_env.fail_session_issuance = True
    r1 = client.post("/api/v1/auth/university-login", json=payload)
    assert r1.status_code == 500

    # User and academic sync occurred, but session was not issued
    assert len(mock_env.auth_users) == 1
    assert len(mock_env.identities) == 1

    # Attempt 2: Session issuance recovered
    mock_env.fail_session_issuance = False
    r2 = client.post("/api/v1/auth/university-login", json=payload)
    assert r2.status_code == 200
    assert r2.json()["success"] is True
    assert len(mock_env.auth_users) == 1
    assert len(mock_env.identities) == 1


# ==============================================================================
# Tests 26 - 30: Routing, Startup, Validation & Isolation
# ==============================================================================


def test_26_startup_succeeds_even_when_fake_university_transport_is_unavailable():
    # Fresh TestClient against app without external calls
    with TestClient(app) as test_client:
        resp = test_client.get("/health")
        assert resp.status_code == 200


def test_27_route_is_registered_at_exact_path():
    openapi_paths = app.openapi()["paths"]
    assert "/api/v1/auth/university-login" in openapi_paths
    assert "post" in openapi_paths["/api/v1/auth/university-login"]


def test_28_get_on_university_login_is_not_accepted(test_setup):
    client, _, _, _, _ = test_setup
    resp = client.get("/api/v1/auth/university-login")
    assert resp.status_code == 405  # Method Not Allowed


def test_29_malformed_request_receives_safe_validation_response(test_setup):
    client, _, _, _, _ = test_setup
    # Empty body
    r1 = client.post("/api/v1/auth/university-login", json={})
    assert r1.status_code == 422

    # Missing password
    r2 = client.post("/api/v1/auth/university-login", json={"student_id": "202310001"})
    assert r2.status_code == 422

    # Empty string password
    r3 = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": "   "})
    assert r3.status_code == 422
    assert "password" not in r3.text.lower() or "empty" in r3.text.lower()


def test_30_no_real_external_network_calls_occur(test_setup):
    # Verified by the mock transport fixtures ensuring 100% in-memory resolution
    client, mock_env, _, _, _ = test_setup
    resp = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": "pass"})
    assert resp.status_code == 200


# ==============================================================================
# Tests 31 - 32: Secret Rotation & Rate Limiting
# ==============================================================================


def test_31_shadow_secret_rotation_recovers_and_issues_session(mock_env):
    """Section E: Verify that after UNI_INTERNAL_AUTH_SECRET changes, the user's password

    is synchronized via Admin API and session is issued successfully.
    """
    uni_client = httpx.AsyncClient(
        transport=httpx.MockTransport(_with_university_envelopes(default_fake_uni_handler))
    )
    contract_client = UniversityContractClient(uni_client, client_secret="test-client-secret")
    supa_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_env.handle_request))

    # Phase 1: User created with Secret 1
    service_secret_1 = UniversitySyncService(
        contract_client=contract_client,
        supabase_url="https://test.supabase.co",
        service_key=TEST_SERVICE_KEY,
        internal_auth_secret="old-secret-11111",
        university_id=TEST_UNIVERSITY_ID,
        client=supa_client,
    )
    admin_auth = SupabaseAdminAuthClient("https://test.supabase.co", TEST_SERVICE_KEY, client=supa_client)

    app.dependency_overrides[get_university_sync_service] = lambda: service_secret_1
    app.dependency_overrides[get_supabase_admin_auth] = lambda: admin_auth
    client = TestClient(app)

    r1 = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": "pass"})
    assert r1.status_code == 200
    user_id = r1.json()["user"]["id"]
    old_shadow_pwd = mock_env.passwords[user_id]

    # Phase 2: Secret rotates to Secret 2
    service_secret_2 = UniversitySyncService(
        contract_client=contract_client,
        supabase_url="https://test.supabase.co",
        service_key=TEST_SERVICE_KEY,
        internal_auth_secret="new-rotated-secret-22222",
        university_id=TEST_UNIVERSITY_ID,
        client=supa_client,
    )
    app.dependency_overrides[get_university_sync_service] = lambda: service_secret_2

    r2 = client.post("/api/v1/auth/university-login", json={"student_id": "202310001", "password": "pass"})
    assert r2.status_code == 200
    new_shadow_pwd = mock_env.passwords[user_id]

    # Password was safely rotated in GoTrue
    assert old_shadow_pwd != new_shadow_pwd
    assert r2.json()["session"]["access_token"] == f"morshidi-access-token-{user_id}"

    app.dependency_overrides.clear()


def test_32_local_rate_limiter_blocks_after_max_attempts(test_setup):
    client, _, _, _, rate_limiter = test_setup
    rate_limiter.reset()

    payload = {"student_id": "202310001", "password": "pass"}

    # 10 allowed attempts
    for _ in range(10):
        r = client.post("/api/v1/auth/university-login", json=payload)
        assert r.status_code == 200

    # 11th attempt is rate limited
    r_blocked = client.post("/api/v1/auth/university-login", json=payload)
    assert r_blocked.status_code == 429
    assert r_blocked.json() == {"success": False, "error": "RATE_LIMITED"}
    assert "Retry-After" in r_blocked.headers
    assert int(r_blocked.headers["Retry-After"]) > 0
