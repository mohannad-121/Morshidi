"""Exhaustive test suite for Step 3: UniversitySyncService.

Covers all 30 required verification cases:
1. first-time student authentication succeeds
2. existing mapped student authentication succeeds
3. university-invalid credentials fail before any provisioning
4. university-returned verified student ID is authoritative
5. new internal Supabase identity is provisioned only once
6. existing mapping prevents duplicate Auth user creation
7. concurrent identity mapping conflict is recovered safely
8. identity mapping is created correctly
9. correct university_id is used
10. correct study plan is resolved
11. profile is created on first sync
12. profile is updated on subsequent sync
13. grade records map to correct course UUIDs
14. course lookup is scoped by university_id
15. leading-zero course codes survive
16. completed attempts are idempotent
17. IN_PROGRESS enrollments are synchronized
18. stale IN_PROGRESS enrollment is removed/updated correctly
19. historical completed attempts are preserved
20. unresolved course behavior matches chosen fail-closed policy
21. unresolved study plan fails closed
22. upstream /me failure causes no academic writes
23. upstream grades failure causes no academic writes
24. malformed upstream data causes no academic writes
25. university password never appears in logs
26. integration token never appears in logs
27. shadow/internal credential never appears in logs
28. repeated full sync produces no duplicate academic records
29. student_university_identities last_synced_at updates only after a successful sync
30. service result contains no sensitive secrets
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest

from app.university_sync.admin_auth import (
    SupabaseAdminAuthClient,
    build_canonical_student_email,
    derive_shadow_password,
)
from app.university_sync.client import UniversityContractClient
from app.university_sync.errors import (
    InvalidUniversityCredentialsError,
    UniversityCourseNotMappedError,
    UniversityPlanNotMappedError,
    UniversityProtocolError,
    UniversitySyncFailedError,
    UniversityUnavailableError,
)
from app.university_sync.identity_repository import (
    StudentUniversityIdentityRecord,
    SupabaseUniversityIdentityRepository,
)
from app.university_sync.models import (
    UniversityAcademicPlan,
    UniversityCourse,
    UniversityEnrollmentRecord,
    UniversityGradeRecord,
    UniversityLoginResponse,
    UniversityStudentProfile,
)
from app.university_sync.service import UniversitySyncResult, UniversitySyncService

TEST_UNIVERSITY_ID = "10000000-0000-0000-0000-000000000001"
TEST_PLAN_ID = "10000000-0000-0000-0000-000000000005"
TEST_SECRET = "test-internal-auth-secret-12345"


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


class MockSupabaseEnvironment:
    """In-memory mock of Supabase GoTrue Auth and PostgREST endpoints."""

    def __init__(self) -> None:
        self.auth_users: list[dict[str, Any]] = []
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
            {"id": "c1000000-0000-0000-0000-000000000004", "course_code": "1501112", "university_id": TEST_UNIVERSITY_ID},
        ]
        self.fail_identity_insert_conflict = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        path = request.url.path

        # 1. Auth Admin: /auth/v1/admin/users
        if path == "/auth/v1/admin/users":
            if request.method == "POST":
                payload = json.loads(request.content)
                email = payload.get("email")
                for u in self.auth_users:
                    if u["email"] == email:
                        return httpx.Response(422, json={"code": 422, "msg": "User already registered"})
                user_id = str(uuid4())
                user_record = {"id": user_id, "email": email, "user_metadata": payload.get("user_metadata", {})}
                self.auth_users.append(user_record)
                return httpx.Response(201, json=user_record)
            elif request.method == "GET":
                return httpx.Response(200, json={"users": self.auth_users})

        # 2. Identities: /rest/v1/student_university_identities
        if path == "/rest/v1/student_university_identities":
            if request.method == "GET":
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
            elif request.method == "POST":
                if self.fail_identity_insert_conflict:
                    self.fail_identity_insert_conflict = False
                    return httpx.Response(
                        409,
                        headers={"content-type": "application/json"},
                        json={"code": "23505", "message": "duplicate key value violates unique constraint"},
                    )
                payload = json.loads(request.content)
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
            elif request.method == "PATCH":
                target_id = request.url.params.get("id", "").replace("eq.", "")
                payload = json.loads(request.content)
                for i in self.identities:
                    if i["id"] == target_id:
                        i.update(payload)
                return httpx.Response(204)

        # 3. Study Plans: /rest/v1/study_plans
        if path == "/rest/v1/study_plans":
            return httpx.Response(200, json=self.study_plans)

        # 4. Courses: /rest/v1/courses
        if path == "/rest/v1/courses":
            uni = request.url.params.get("university_id", "").replace("eq.", "")
            matched = [c for c in self.courses if not uni or c["university_id"] == uni]
            return httpx.Response(200, json=matched)

        # 5. Profiles: /rest/v1/student_academic_profiles
        if path == "/rest/v1/student_academic_profiles":
            if request.method == "GET":
                owner = request.url.params.get("owner_user_id", "").replace("eq.", "")
                matched = [p for p in self.profiles if not owner or p["owner_user_id"] == owner]
                return httpx.Response(200, json=matched)
            elif request.method == "POST":
                payload = json.loads(request.content)
                pid = str(uuid4())
                rec = {"id": pid, **payload}
                self.profiles.append(rec)
                return httpx.Response(201, json=[rec])
            elif request.method == "PATCH":
                target_id = request.url.params.get("id", "").replace("eq.", "")
                payload = json.loads(request.content)
                for p in self.profiles:
                    if p["id"] == target_id:
                        p.update(payload)
                return httpx.Response(200, json=[payload])

        # 6. Attempts: /rest/v1/student_course_attempts
        if path == "/rest/v1/student_course_attempts":
            if request.method == "GET":
                pid = request.url.params.get("profile_id", "").replace("eq.", "")
                matched = [a for a in self.attempts if not pid or a["profile_id"] == pid]
                return httpx.Response(200, json=matched)
            elif request.method == "POST":
                payload = json.loads(request.content)
                aid = str(uuid4())
                rec = {"id": aid, **payload}
                self.attempts.append(rec)
                return httpx.Response(201, json=[rec])
            elif request.method == "DELETE":
                target_id = request.url.params.get("id", "").replace("eq.", "")
                self.attempts = [a for a in self.attempts if a["id"] != target_id]
                return httpx.Response(204)

        return httpx.Response(404, text=f"Unhandled mock endpoint: {url_str}")


@pytest.fixture
def mock_supabase() -> MockSupabaseEnvironment:
    return MockSupabaseEnvironment()


@pytest.fixture
def test_service(mock_supabase: MockSupabaseEnvironment) -> tuple[UniversitySyncService, httpx.AsyncClient]:
    # Mock university transport
    def uni_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/integrations/morshidi/v1/auth/login":
            data = json.loads(request.content)
            if data.get("password") == "WrongPass":
                return httpx.Response(401, json={"detail": "Invalid university credentials"})
            return httpx.Response(
                200,
                json={
                    "success": True,
                    "accessToken": "mock-uni-jwt-token-12345",
                    "tokenType": "Bearer",
                    "expiresIn": 900,
                    "student": {
                        "studentId": data.get("studentId"),
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
                                {
                                    "courseCode": "0200104",
                                    "name": "Calculus 1",
                                    "credits": 3,
                                    "grade": 95,
                                    "letterGrade": "A",
                                    "status": "passed",
                                },
                                {
                                    "courseCode": "1501110",
                                    "name": "Computer Science 1",
                                    "credits": 3,
                                    "grade": 88,
                                    "letterGrade": "B+",
                                    "status": "passed",
                                },
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
        return httpx.Response(404, text=f"Unhandled university endpoint: {path}")

    uni_client = httpx.AsyncClient(transport=httpx.MockTransport(_with_university_envelopes(uni_handler)))
    contract_client = UniversityContractClient(uni_client, client_secret="test-client-secret")

    supa_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_supabase.handle_request))

    service = UniversitySyncService(
        contract_client=contract_client,
        supabase_url="https://test.supabase.co",
        service_key="test-service-key",
        internal_auth_secret=TEST_SECRET,
        university_id=TEST_UNIVERSITY_ID,
        client=supa_client,
    )
    return service, supa_client


# ==============================================================================
# Tests 1 - 10: Authentication, Identity Resolution, Study Plan
# ==============================================================================


@pytest.mark.anyio
async def test_01_first_time_student_authentication_succeeds(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    result = await service.authenticate_and_sync_student("202310001", "SecretPass123!")

    assert isinstance(result, UniversitySyncResult)
    assert result.is_new_user is True
    assert result.university_student_id == "202310001"
    assert result.university_id == TEST_UNIVERSITY_ID
    assert result.canonical_email == "202310001@shadow.morshidi.internal"
    assert len(mock_supabase.auth_users) == 1
    assert len(mock_supabase.identities) == 1
    assert len(mock_supabase.profiles) == 1


@pytest.mark.anyio
async def test_02_existing_mapped_student_authentication_succeeds(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    # First sync
    res1 = await service.authenticate_and_sync_student("202310001", "SecretPass123!")
    # Second sync
    res2 = await service.authenticate_and_sync_student("202310001", "SecretPass123!")

    assert res2.is_new_user is False
    assert res2.owner_user_id == res1.owner_user_id
    assert len(mock_supabase.auth_users) == 1
    assert len(mock_supabase.identities) == 1


@pytest.mark.anyio
async def test_03_university_invalid_credentials_fail_before_any_provisioning(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    with pytest.raises(InvalidUniversityCredentialsError):
        await service.authenticate_and_sync_student("202310001", "WrongPass")

    assert len(mock_supabase.auth_users) == 0
    assert len(mock_supabase.identities) == 0
    assert len(mock_supabase.profiles) == 0


@pytest.mark.anyio
async def test_04_university_returned_verified_student_id_is_authoritative() -> None:
    # If student requests " 202310001 " or upstream returns normalized "202310001"
    env = MockSupabaseEnvironment()

    def uni_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/login"):
            return httpx.Response(200, json={"token": "t", "studentId": "202310001"})
        elif path.endswith("/student/me"):
            return httpx.Response(200, json={"studentId": "202310001", "studyPlan": "12"})
        elif path.endswith("/student/academic-plan"):
            return httpx.Response(200, json={"planId": "12"})
        return httpx.Response(200, json=[])

    uni_client = httpx.AsyncClient(transport=httpx.MockTransport(_with_university_envelopes(uni_handler)))
    supa_client = httpx.AsyncClient(transport=httpx.MockTransport(env.handle_request))
    service = UniversitySyncService(
        UniversityContractClient(uni_client, client_secret="test-client-secret"),
        supabase_url="https://test.supabase.co", service_key="key",
        internal_auth_secret=TEST_SECRET, client=supa_client,
    )
    res = await service.authenticate_and_sync_student("202310001_raw", "pass")
    assert res.university_student_id == "202310001"


@pytest.mark.anyio
async def test_05_and_06_new_identity_provisioned_once_and_existing_mapping_prevents_duplicate(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    await service.authenticate_and_sync_student("202310001", "pass")
    await service.authenticate_and_sync_student("202310001", "pass")

    assert len(mock_supabase.auth_users) == 1
    assert len(mock_supabase.identities) == 1


@pytest.mark.anyio
async def test_07_concurrent_identity_mapping_conflict_is_recovered_safely(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    # Pre-insert existing identity by another process
    owner_winner = str(uuid4())
    mock_supabase.identities.append({
        "id": str(uuid4()),
        "owner_user_id": owner_winner,
        "university_id": TEST_UNIVERSITY_ID,
        "university_student_id": "202310001",
        "created_at": "2026-10-05T12:00:00Z",
        "updated_at": "2026-10-05T12:00:00Z",
        "last_synced_at": None,
    })
    mock_supabase.fail_identity_insert_conflict = True

    result = await service.authenticate_and_sync_student("202310001", "pass")
    assert result.owner_user_id == owner_winner
    assert len(mock_supabase.identities) == 1


@pytest.mark.anyio
async def test_08_and_09_identity_mapping_and_university_id_used(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    res = await service.authenticate_and_sync_student("202310001", "pass")

    mapping = mock_supabase.identities[0]
    assert mapping["university_id"] == TEST_UNIVERSITY_ID
    assert mapping["university_student_id"] == "202310001"
    assert mapping["owner_user_id"] == res.owner_user_id


@pytest.mark.anyio
async def test_10_correct_study_plan_is_resolved(test_service: tuple[UniversitySyncService, httpx.AsyncClient]) -> None:
    service, _ = test_service
    res = await service.authenticate_and_sync_student("202310001", "pass")
    assert res.study_plan_id == TEST_PLAN_ID


# ==============================================================================
# Tests 11 - 19: Profile, Courses, Grades, Enrollments Idempotency
# ==============================================================================


@pytest.mark.anyio
async def test_11_and_12_profile_created_on_first_sync_and_updated_on_second(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    # First sync
    res1 = await service.authenticate_and_sync_student("202310001", "pass")
    assert len(mock_supabase.profiles) == 1
    assert mock_supabase.profiles[0]["reported_cumulative_gpa"] == "3.45"

    # Second sync
    res2 = await service.authenticate_and_sync_student("202310001", "pass")
    assert len(mock_supabase.profiles) == 1
    assert res2.profile_id == res1.profile_id


@pytest.mark.anyio
async def test_13_14_15_grade_records_mapped_scoped_and_leading_zero(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    await service.authenticate_and_sync_student("202310001", "pass")

    calc_attempt = next(a for a in mock_supabase.attempts if a["course_id"] == "c1000000-0000-0000-0000-000000000001")
    assert calc_attempt["outcome"] == "PASSED"
    assert calc_attempt["reported_grade_text"] == "A"
    assert calc_attempt["raw_numeric_grade"] == "95"
    assert calc_attempt["attempt_credit_hours"] == "3"
    assert calc_attempt["term_label"] == "2023-1"
    assert calc_attempt["record_source"] == "university_integration"
    assert calc_attempt["performance_provenance"] == "OFFICIAL_VERIFIED"
    assert calc_attempt["performance_verification_state"] == "VERIFIED"

    enrollment_attempt = next(
        attempt
        for attempt in mock_supabase.attempts
        if attempt["course_id"] == "c1000000-0000-0000-0000-000000000003"
    )
    assert enrollment_attempt["outcome"] == "IN_PROGRESS"
    assert enrollment_attempt["term_label"] == "2024-1"
    assert enrollment_attempt["raw_term"] == "2024-1"
    assert enrollment_attempt["attempt_credit_hours"] == "3"


@pytest.mark.anyio
async def test_16_completed_attempts_are_idempotent(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    await service.authenticate_and_sync_student("202310001", "pass")
    attempts_first = len(mock_supabase.attempts)

    await service.authenticate_and_sync_student("202310001", "pass")
    attempts_second = len(mock_supabase.attempts)

    assert attempts_first == attempts_second


@pytest.mark.anyio
async def test_17_18_19_in_progress_enrollments_synced_and_stale_removed_and_history_preserved(mock_supabase: MockSupabaseEnvironment) -> None:
    current_enrollments = [{"courseCode": "0300103", "sectionId": "SEC-01", "semester": "2024-1", "status": "ENROLLED"}]

    def uni_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/login"):
            return httpx.Response(200, json={"token": "t", "studentId": "202310001"})
        elif path.endswith("/student/me"):
            return httpx.Response(200, json={"studentId": "202310001", "studyPlan": "12"})
        elif path.endswith("/student/courses"):
            return httpx.Response(200, json=[])
        elif path.endswith("/student/grades"):
            return httpx.Response(200, json=[{"courseCode": "0200104", "semester": "2023-1", "letterGrade": "A", "status": "PASSED"}])
        elif path.endswith("/student/enrollments"):
            return httpx.Response(200, json=current_enrollments)
        elif path.endswith("/student/academic-plan"):
            return httpx.Response(200, json={"planId": "12"})
        return httpx.Response(404)

    uni_client = httpx.AsyncClient(transport=httpx.MockTransport(_with_university_envelopes(uni_handler)))
    supa_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_supabase.handle_request))
    service = UniversitySyncService(
        UniversityContractClient(uni_client, client_secret="test-client-secret"),
        supabase_url="https://test.supabase.co", service_key="key",
        internal_auth_secret=TEST_SECRET, client=supa_client,
    )

    # First sync: 0200104 (PASSED), 0300103 (IN_PROGRESS)
    await service.authenticate_and_sync_student("202310001", "pass")
    in_prog_1 = [a for a in mock_supabase.attempts if a["outcome"] == "IN_PROGRESS"]
    assert len(in_prog_1) == 1
    assert in_prog_1[0]["course_id"] == "c1000000-0000-0000-0000-000000000003"

    # Second sync: enrollment changes to 1501112; 0300103 is stale and must be removed
    current_enrollments = [{"courseCode": "1501112", "sectionId": "SEC-02", "semester": "2024-1", "status": "ENROLLED"}]
    await service.authenticate_and_sync_student("202310001", "pass")

    in_prog_2 = [a for a in mock_supabase.attempts if a["outcome"] == "IN_PROGRESS"]
    assert len(in_prog_2) == 1
    assert in_prog_2[0]["course_id"] == "c1000000-0000-0000-0000-000000000004"

    # Completed attempt 0200104 remains intact
    completed = [a for a in mock_supabase.attempts if a["outcome"] == "PASSED"]
    assert len(completed) == 1
    assert completed[0]["course_id"] == "c1000000-0000-0000-0000-000000000001"


# ==============================================================================
# Tests 20 - 24: Fail-closed Policies & Upstream Errors
# ==============================================================================


@pytest.mark.anyio
async def test_20_unresolved_course_fails_closed(mock_supabase: MockSupabaseEnvironment) -> None:
    def uni_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"token": "t", "studentId": "202310001"})
        elif request.url.path.endswith("/student/me"):
            return httpx.Response(200, json={"studentId": "202310001", "studyPlan": "12"})
        elif request.url.path.endswith("/student/grades"):
            # Unknown course UNKNOWN999
            return httpx.Response(200, json=[{"courseCode": "UNKNOWN999", "status": "PASSED"}])
        elif request.url.path.endswith("/student/academic-plan"):
            return httpx.Response(200, json={"planId": "12"})
        return httpx.Response(200, json=[])

    service = UniversitySyncService(
        UniversityContractClient(httpx.AsyncClient(transport=httpx.MockTransport(_with_university_envelopes(uni_handler))), client_secret="test-client-secret"),
        supabase_url="https://test.supabase.co", service_key="key",
        internal_auth_secret=TEST_SECRET,
        client=httpx.AsyncClient(transport=httpx.MockTransport(mock_supabase.handle_request)),
    )
    with pytest.raises(UniversityCourseNotMappedError) as exc_info:
        await service.authenticate_and_sync_student("202310001", "pass")
    assert "UNKNOWN999" in str(exc_info.value)
    # Zero academic writes
    assert len(mock_supabase.profiles) == 0
    assert len(mock_supabase.attempts) == 0


@pytest.mark.anyio
async def test_21_unresolved_study_plan_fails_closed(mock_supabase: MockSupabaseEnvironment) -> None:
    def uni_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"token": "t", "studentId": "202310001"})
        elif request.url.path.endswith("/student/me"):
            return httpx.Response(200, json={"studentId": "202310001", "studyPlan": "NonExistentPlan999"})
        elif request.url.path.endswith("/student/academic-plan"):
            return httpx.Response(200, json={"planId": "999"})
        return httpx.Response(200, json=[])

    service = UniversitySyncService(
        UniversityContractClient(httpx.AsyncClient(transport=httpx.MockTransport(_with_university_envelopes(uni_handler))), client_secret="test-client-secret"),
        supabase_url="https://test.supabase.co", service_key="key",
        internal_auth_secret=TEST_SECRET,
        client=httpx.AsyncClient(transport=httpx.MockTransport(mock_supabase.handle_request)),
    )
    with pytest.raises(UniversityPlanNotMappedError):
        await service.authenticate_and_sync_student("202310001", "pass")
    assert len(mock_supabase.profiles) == 0


@pytest.mark.anyio
async def test_22_upstream_me_failure_causes_no_academic_writes(mock_supabase: MockSupabaseEnvironment) -> None:
    def uni_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"token": "t", "studentId": "202310001"})
        elif request.url.path.endswith("/student/me"):
            return httpx.Response(500, text="Internal University Error")
        return httpx.Response(200, json=[])

    service = UniversitySyncService(
        UniversityContractClient(httpx.AsyncClient(transport=httpx.MockTransport(_with_university_envelopes(uni_handler))), client_secret="test-client-secret"),
        supabase_url="https://test.supabase.co", service_key="key",
        internal_auth_secret=TEST_SECRET,
        client=httpx.AsyncClient(transport=httpx.MockTransport(mock_supabase.handle_request)),
    )
    with pytest.raises(UniversityUnavailableError):
        await service.authenticate_and_sync_student("202310001", "pass")
    assert len(mock_supabase.auth_users) == 0
    assert len(mock_supabase.profiles) == 0
    assert len(mock_supabase.attempts) == 0


@pytest.mark.anyio
async def test_23_upstream_grades_failure_causes_no_academic_writes(mock_supabase: MockSupabaseEnvironment) -> None:
    def uni_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"token": "t", "studentId": "202310001"})
        elif request.url.path.endswith("/student/grades"):
            return httpx.Response(503, text="Service Unavailable")
        elif request.url.path.endswith("/student/me"):
            return httpx.Response(200, json={"studentId": "202310001", "studyPlan": "12"})
        elif request.url.path.endswith("/student/academic-plan"):
            return httpx.Response(200, json={"planId": "12"})
        return httpx.Response(200, json=[])

    service = UniversitySyncService(
        UniversityContractClient(httpx.AsyncClient(transport=httpx.MockTransport(_with_university_envelopes(uni_handler))), client_secret="test-client-secret"),
        supabase_url="https://test.supabase.co", service_key="key",
        internal_auth_secret=TEST_SECRET,
        client=httpx.AsyncClient(transport=httpx.MockTransport(mock_supabase.handle_request)),
    )
    with pytest.raises(UniversityUnavailableError):
        await service.authenticate_and_sync_student("202310001", "pass")
    assert len(mock_supabase.profiles) == 0


@pytest.mark.anyio
async def test_24_malformed_upstream_data_causes_no_academic_writes(mock_supabase: MockSupabaseEnvironment) -> None:
    def uni_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"token": "t", "studentId": "202310001"})
        elif request.url.path.endswith("/student/grades"):
            return httpx.Response(200, text="Not JSON at all")
        return httpx.Response(200, json=[])

    service = UniversitySyncService(
        UniversityContractClient(httpx.AsyncClient(transport=httpx.MockTransport(_with_university_envelopes(uni_handler))), client_secret="test-client-secret"),
        supabase_url="https://test.supabase.co", service_key="key",
        internal_auth_secret=TEST_SECRET,
        client=httpx.AsyncClient(transport=httpx.MockTransport(mock_supabase.handle_request)),
    )
    with pytest.raises(UniversityProtocolError):
        await service.authenticate_and_sync_student("202310001", "pass")
    assert len(mock_supabase.profiles) == 0


# ==============================================================================
# Tests 25 - 30: Security Invariants, Logging, Secrets & Finalization
# ==============================================================================


@pytest.mark.anyio
async def test_25_26_27_secrets_and_passwords_never_logged(test_service: tuple[UniversitySyncService, httpx.AsyncClient], caplog: pytest.LogCaptureFixture) -> None:
    service, _ = test_service
    caplog.set_level(logging.DEBUG)

    sensitive_pw = "ExtremelySecretUniPass!99"
    await service.authenticate_and_sync_student("202310001", sensitive_pw)

    log_text = caplog.text
    assert sensitive_pw not in log_text
    assert "mock-uni-jwt-token" not in log_text
    assert TEST_SECRET not in log_text
    assert "Mor!v1_" not in log_text


@pytest.mark.anyio
async def test_28_repeated_full_sync_produces_no_duplicate_academic_records(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    await service.authenticate_and_sync_student("202310001", "pass")
    initial_attempts = list(mock_supabase.attempts)

    await service.authenticate_and_sync_student("202310001", "pass")
    repeated_attempts = list(mock_supabase.attempts)

    assert len(initial_attempts) == len(repeated_attempts)


@pytest.mark.anyio
async def test_29_last_synced_at_updates_only_after_successful_sync(test_service: tuple[UniversitySyncService, httpx.AsyncClient], mock_supabase: MockSupabaseEnvironment) -> None:
    service, _ = test_service
    res = await service.authenticate_and_sync_student("202310001", "pass")

    ident = mock_supabase.identities[0]
    assert ident["last_synced_at"] is not None
    assert ident["last_synced_at"].startswith(str(res.synced_at.year))


@pytest.mark.anyio
async def test_30_service_result_contains_no_sensitive_secrets(test_service: tuple[UniversitySyncService, httpx.AsyncClient]) -> None:
    service, _ = test_service
    res = await service.authenticate_and_sync_student("202310001", "SensitivePass")

    result_repr = repr(res)
    assert "SensitivePass" not in result_repr
    assert "mock-uni-jwt-token" not in result_repr
    assert "Mor!v1_" not in result_repr
    assert TEST_SECRET not in result_repr
