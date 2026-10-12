"""Opt-in end-to-end grading-policy proof against isolated Local Supabase only."""

from __future__ import annotations

import os
import uuid
from urllib.parse import urlparse

import httpx
import pytest

from app.catalog.supabase_repository import SupabaseAcademicCatalogRepository
from app.services.eligibility import EligibilityService
from app.services.student import StudentService
from app.student.supabase_repository import SupabaseStudentAcademicRepository
from app.student_intelligence.adaptive import (
    FAKE_UNIVERSITY_GRADING_POLICY_V1,
    GradePolicyRegistry,
)
from app.university_sync.client import UniversityContractClient
from app.university_sync.errors import UniversityProtocolError
from app.university_sync.service import UniversitySyncService


URL = os.getenv("MORSHIDI_LOCAL_SUPABASE_URL")
SERVER_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_SERVER_KEY")
PLAN12 = os.getenv("MORSHIDI_LOCAL_STUDY_PLAN_ID", "10000000-0000-0000-0000-000000000005")
UNIVERSITY = "10000000-0000-0000-0000-000000000001"
pytestmark = pytest.mark.skipif(
    not all((URL, SERVER_KEY)), reason="set local-only MORSHIDI_LOCAL_SUPABASE_* values")


def _university_handler(student_id: str, *, valid_policy: bool = True):
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/auth/login"):
            return httpx.Response(200, json={"token": "local-upstream-token", "studentId": student_id})
        if path.endswith("/student/me"):
            return httpx.Response(200, json={"success": True, "student": {
                "studentId": student_id, "name": "Local Contract Student",
                "email": f"{student_id}@local.test", "faculty": "IT", "major": "AI",
                "degree": "Bachelor", "studyType": "Regular", "admissionYear": 2023,
                "academicAdvisor": "Local Advisor", "academicStatus": "active",
                "gpa": 93.6, "gpaScale": 100, "earnedCredits": 96,
            }})
        if path.endswith("/student/courses"):
            return httpx.Response(200, json={"success": True, "courses": {
                "completed": [{"courseCode": "1501110", "name": "Computer Science 1",
                               "credits": 3, "status": "completed"}],
                "current": [], "remaining": [],
            }})
        if path.endswith("/student/grades"):
            payload = {"success": True, "cumulativeGpa": 93.6, "gpaScale": 100,
                "semesters": [{"term": "2023-1", "termLabel": "First Semester 2023",
                    "registeredHours": 3, "passedHours": 3, "semesterGpa": 93.6,
                    "cumulativeGpa": 93.6, "courses": [{"courseCode": "1501110",
                        "name": "Computer Science 1", "credits": 3, "grade": 54,
                        "letterGrade": "D", "status": "passed"}]}]}
            if valid_policy:
                payload["gradingPolicy"] = {"version": "FAKE_UNIVERSITY_GRADING_POLICY_V1",
                    "gpa": {"numericMin": 0, "numericMax": 100, "scale": 100},
                    "courseGrade": {"numericMin": 0, "numericMax": 100}}
            return httpx.Response(200, json=payload)
        if path.endswith("/student/enrollments"):
            return httpx.Response(200, json={"success": True, "term": "2026-1",
                                             "termLabel": "First Semester 2026", "enrollments": []})
        if path.endswith("/student/academic-plan"):
            return httpx.Response(200, json={"success": True, "plan": {
                "planId": "12", "major": "AI", "totalRequiredCredits": 132,
                "earnedCredits": 96, "remainingCredits": 36, "courses": []}})
        return httpx.Response(404)
    return handler


@pytest.mark.anyio
async def test_policy_bound_resync_persists_and_survives_service_reconstruction() -> None:
    assert urlparse(URL or "").hostname in {"localhost", "127.0.0.1", "::1"}
    student_id = f"policy-{uuid.uuid4().hex}"
    headers = {"apikey": SERVER_KEY or "", "Authorization": f"Bearer {SERVER_KEY or ''}",
               "Content-Type": "application/json"}
    local_client = httpx.AsyncClient(base_url=URL, headers=headers)
    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(
        _university_handler(student_id)))
    sync = UniversitySyncService(
        UniversityContractClient(upstream_client, client_secret="local-test-secret"),
        supabase_url=URL, service_key=SERVER_KEY, internal_auth_secret="local-internal-secret",
        university_id=UNIVERSITY, client=local_client)
    owner_id = None
    try:
        first = await sync.authenticate_and_sync_student(student_id, "password")
        owner_id = first.owner_user_id
        attempts_response = await local_client.get("/rest/v1/student_course_attempts", params={
            "profile_id": f"eq.{first.profile_id}", "select": "*"})
        attempts_response.raise_for_status()
        attempts = attempts_response.json()
        completed = next(row for row in attempts if row["outcome"] == "PASSED")
        attempt_id = completed["id"]
        sequence = completed["attempt_sequence"]

        # Model a stored pre-contract record without changing identity/history.
        old_patch = await local_client.patch("/rest/v1/student_course_attempts", params={
            "id": f"eq.{attempt_id}"}, json={"performance_source_reference": None})
        old_patch.raise_for_status()

        repository = SupabaseStudentAcademicRepository(URL or "", SERVER_KEY or "", local_client)
        catalog = SupabaseAcademicCatalogRepository(URL or "", SERVER_KEY or "", local_client)
        student_service = StudentService(repository, EligibilityService(catalog), catalog,
            grade_policies=GradePolicyRegistry((FAKE_UNIVERSITY_GRADING_POLICY_V1,)))
        old_profile = await student_service.get_student_intelligence_v2(owner_id)
        assert old_profile.verified_grade_count == 0

        second = await sync.authenticate_and_sync_student(student_id, "password")
        assert second.profile_id == first.profile_id
        rows = (await local_client.get("/rest/v1/student_course_attempts", params={
            "profile_id": f"eq.{first.profile_id}", "select": "*"})).json()
        completed_rows = [row for row in rows if row["outcome"] == "PASSED"]
        assert len(completed_rows) == 1
        assert completed_rows[0]["id"] == attempt_id
        assert completed_rows[0]["attempt_sequence"] == sequence
        assert completed_rows[0]["performance_source_reference"] == (
            f"university:{UNIVERSITY}:grading-policy:FAKE_UNIVERSITY_GRADING_POLICY_V1")

        # A reconstructed service proves policy resolution is not in-memory sync state.
        reconstructed = StudentService(repository, EligibilityService(catalog), catalog,
            grade_policies=GradePolicyRegistry((FAKE_UNIVERSITY_GRADING_POLICY_V1,)))
        trusted_profile = await reconstructed.get_student_intelligence_v2(owner_id)
        assert trusted_profile.verified_grade_count == 1
        assert any(row.skill_id == "PROGRAMMING" and row.score == 54
                   for row in trusted_profile.skills)
        assert old_profile.source_snapshot_version != trusted_profile.source_snapshot_version

        third = await sync.authenticate_and_sync_student(student_id, "password")
        assert third.profile_id == first.profile_id
        repeated = (await local_client.get("/rest/v1/student_course_attempts", params={
            "profile_id": f"eq.{first.profile_id}", "select": "id,attempt_sequence,outcome"})).json()
        assert [(row["id"], row["attempt_sequence"]) for row in repeated if row["outcome"] == "PASSED"] == [
            (attempt_id, sequence)]

        before_profile = (await local_client.get("/rest/v1/student_academic_profiles", params={
            "id": f"eq.{first.profile_id}", "select": "*"})).json()
        before_attempts = (await local_client.get("/rest/v1/student_course_attempts", params={
            "profile_id": f"eq.{first.profile_id}", "select": "*", "order": "id"})).json()
        invalid_upstream = httpx.AsyncClient(transport=httpx.MockTransport(
            _university_handler(student_id, valid_policy=False)))
        invalid_sync = UniversitySyncService(
            UniversityContractClient(invalid_upstream, client_secret="local-test-secret"),
            supabase_url=URL, service_key=SERVER_KEY, internal_auth_secret="local-internal-secret",
            university_id=UNIVERSITY, client=local_client)
        with pytest.raises(UniversityProtocolError):
            await invalid_sync.authenticate_and_sync_student(student_id, "password")
        await invalid_upstream.aclose()
        after_profile = (await local_client.get("/rest/v1/student_academic_profiles", params={
            "id": f"eq.{first.profile_id}", "select": "*"})).json()
        after_attempts = (await local_client.get("/rest/v1/student_course_attempts", params={
            "profile_id": f"eq.{first.profile_id}", "select": "*", "order": "id"})).json()
        assert after_profile == before_profile
        assert after_attempts == before_attempts
    finally:
        if owner_id:
            await local_client.delete("/rest/v1/student_university_identities", params={
                "owner_user_id": f"eq.{owner_id}"})
            await local_client.delete("/rest/v1/student_academic_profiles", params={
                "owner_user_id": f"eq.{owner_id}"})
            await local_client.delete(f"/auth/v1/admin/users/{owner_id}")
        await upstream_client.aclose()
        await local_client.aclose()
