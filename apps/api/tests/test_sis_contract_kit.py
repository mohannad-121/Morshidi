"""Reusable SIS Contract Test Kit verifying adherence to MORSHIDI_SIS_CONTRACT_V1."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
import pytest
import httpx

from app.sis_integration.adapter_interface import SISAdapter
from app.sis_integration.capabilities import SISCapability
from app.sis_integration.generic_rest_adapter import GenericRestAdapter
from app.sis_integration.models import (
    HealthResult,
    NormalizedCourse,
    NormalizedEnrollment,
    NormalizedGradeAttempt,
    NormalizedOffering,
    NormalizedStudent,
    NormalizedStudyPlan,
    NormalizedTerm,
    UniversityIntegrationConfig,
)


class SISContractTestKit:
    """Verifies that any SISAdapter implementation strictly satisfies MORSHIDI_SIS_CONTRACT_V1."""

    @staticmethod
    async def verify_health_check(adapter: SISAdapter) -> HealthResult:
        res = await adapter.health_check()
        assert isinstance(res, HealthResult)
        assert res.status in {"HEALTHY", "DEGRADED", "UNHEALTHY", "NOT_CONFIGURED"}
        assert isinstance(res.connectivity, bool)
        assert isinstance(res.latency_ms, (int, float))
        return res

    @staticmethod
    async def verify_student_profile(adapter: SISAdapter, student_id: str, token: str) -> NormalizedStudent:
        if SISCapability.STUDENT_PROFILE_READ not in adapter.capabilities:
            pytest.skip("STUDENT_PROFILE_READ not supported by adapter")
        profile = await adapter.get_student_profile(student_id, token)
        assert isinstance(profile, NormalizedStudent)
        assert profile.contract_version == "MORSHIDI_SIS_CONTRACT_V1"
        assert profile.university_student_id == student_id
        return profile

    @staticmethod
    async def verify_grades(adapter: SISAdapter, student_id: str, token: str) -> list[NormalizedGradeAttempt]:
        if SISCapability.GRADES_READ not in adapter.capabilities:
            pytest.skip("GRADES_READ not supported by adapter")
        grades = await adapter.get_grades(student_id, token)
        assert isinstance(grades, list)
        for g in grades:
            assert isinstance(g, NormalizedGradeAttempt)
            assert g.contract_version == "MORSHIDI_SIS_CONTRACT_V1"
            assert g.outcome in {"PASSED", "FAILED", "WITHDRAWN", "IN_PROGRESS"}
            assert len(g.course_code) > 0
        return grades

    @staticmethod
    async def verify_enrollments(adapter: SISAdapter, student_id: str, token: str) -> list[NormalizedEnrollment]:
        if SISCapability.ENROLLMENTS_READ not in adapter.capabilities:
            pytest.skip("ENROLLMENTS_READ not supported by adapter")
        enrollments = await adapter.get_enrollments(student_id, token)
        assert isinstance(enrollments, list)
        for e in enrollments:
            assert isinstance(e, NormalizedEnrollment)
            assert e.contract_version == "MORSHIDI_SIS_CONTRACT_V1"
            assert e.status in {"ENROLLED", "WAITLISTED", "DROPPED"}
        return enrollments

    @staticmethod
    async def verify_terms(adapter: SISAdapter) -> list[NormalizedTerm]:
        terms = await adapter.get_terms()
        assert isinstance(terms, list)
        for t in terms:
            assert isinstance(t, NormalizedTerm)
            assert t.contract_version == "MORSHIDI_SIS_CONTRACT_V1"
            assert len(t.term_code) > 0
        return terms

    @staticmethod
    async def verify_offerings(adapter: SISAdapter, term_code: str) -> list[NormalizedOffering]:
        if SISCapability.OFFERINGS_READ not in adapter.capabilities:
            pytest.skip("OFFERINGS_READ not supported by adapter")
        offerings = await adapter.get_course_offerings(term_code)
        assert isinstance(offerings, list)
        for o in offerings:
            assert isinstance(o, NormalizedOffering)
            assert o.contract_version == "MORSHIDI_SIS_CONTRACT_V1"
            assert len(o.section_id) > 0
            assert o.capacity >= 0
            assert o.enrolled >= 0
            assert o.available >= 0
        return offerings


@pytest.mark.anyio
async def test_generic_rest_adapter_conforms_to_contract_kit():
    """Verify GenericRestAdapter conforms to all normalized DTO contracts via SISContractTestKit."""
    config = UniversityIntegrationConfig(
        university_id="10000000-0000-0000-0000-000000000002",  # type: ignore[arg-type]
        provider_type="generic_rest",
        base_url="https://sis.partner-university.edu/api/v1",
        auth_method="token",
        secret_env_ref="MOCK_SIS_TOKEN",
        supported_capabilities=[
            SISCapability.IDENTITY_AUTH,
            SISCapability.STUDENT_PROFILE_READ,
            SISCapability.GRADES_READ,
            SISCapability.ENROLLMENTS_READ,
            SISCapability.OFFERINGS_READ,
            SISCapability.CURRICULUM_READ,
        ],
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        if url_path == "/api/v1/health":
            return httpx.Response(200, json={"status": "ok", "service": "Partner-SIS", "timestamp": "2026-10-20T00:00:00Z"}, headers={"content-type": "application/json"})
        if url_path == "/api/v1/students/2026001":
            return httpx.Response(200, json={
                "student_id": "2026001",
                "full_name": "Tariq Ahmad",
                "email": "tariq@partner-university.edu",
                "faculty_code": "ENG",
                "major_code": "CS",
                "plan_number": "2024",
                "academic_standing": "GOOD_STANDING",
                "cumulative_gpa": "3.65",
                "gpa_scale": "4.00",
                "earned_credit_hours": "64.0",
            })
        if url_path == "/api/v1/students/2026001/grades":
            return httpx.Response(200, json=[
                {"course_code": "CS101", "term_code": "2025-1", "outcome": "PASSED", "numeric_grade": "88", "letter_grade": "B+", "credit_hours": "3"},
                {"course_code": "MATH101", "term_code": "2025-1", "outcome": "PASSED", "numeric_grade": "92", "letter_grade": "A-", "credit_hours": "3"},
            ])
        if url_path == "/api/v1/students/2026001/enrollments":
            return httpx.Response(200, json=[
                {"course_code": "CS201", "section_code": "SEC-01", "term_code": "2026-1", "status": "ENROLLED", "credit_hours": "3"}
            ])
        if url_path == "/api/v1/terms":
            return httpx.Response(200, json=[
                {"term_code": "2026-1", "term_name_ar": "الفصل الأول 2026", "is_current": True, "is_registration_open": True}
            ])
        if url_path == "/api/v1/offerings":
            return httpx.Response(200, json=[
                {"section_id": "CS201-01", "course_code": "CS201", "section_number": "1", "capacity": 35, "enrolled": 30, "available": 5, "status": "OPEN"}
            ])
        return httpx.Response(404, json={"detail": "Not found"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_handler)) as client:
        adapter = GenericRestAdapter(config, http_client=client)

        # 1. Health check verification
        health = await SISContractTestKit.verify_health_check(adapter)
        assert health.status == "HEALTHY"
        assert health.connectivity is True

        # 2. Student profile verification
        profile = await SISContractTestKit.verify_student_profile(adapter, "2026001", "mock-token")
        assert profile.full_name == "Tariq Ahmad"
        assert profile.cumulative_gpa == Decimal("3.65")
        assert profile.earned_credit_hours == Decimal("64.0")

        # 3. Grades verification
        grades = await SISContractTestKit.verify_grades(adapter, "2026001", "mock-token")
        assert len(grades) == 2
        assert grades[0].course_code == "CS101"
        assert grades[0].outcome == "PASSED"

        # 4. Enrollments verification
        enrollments = await SISContractTestKit.verify_enrollments(adapter, "2026001", "mock-token")
        assert len(enrollments) == 1
        assert enrollments[0].course_code == "CS201"
        assert enrollments[0].status == "ENROLLED"

        # 5. Terms verification
        terms = await SISContractTestKit.verify_terms(adapter)
        assert len(terms) == 1
        assert terms[0].term_code == "2026-1"

        # 6. Offerings verification
        offerings = await SISContractTestKit.verify_offerings(adapter, "2026-1")
        assert len(offerings) == 1
        assert offerings[0].section_id == "CS201-01"
        assert offerings[0].available == 5


@pytest.mark.anyio
async def test_fake_university_adapter_conforms_to_contract_kit():
    """Verify FakeUniversityAdapter conforms to all normalized DTO contracts via SISContractTestKit."""
    from app.sis_integration.fake_university_adapter import FakeUniversityAdapter
    from app.university_sync.client import UniversityContractClient

    def mock_fake_uni_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/healthz":
            return httpx.Response(200, json={"ok": True, "ready": True, "cursor": 9})
        if path == "/api/integrations/morshidi/v1/student/me":
            return httpx.Response(200, json={
                "success": True,
                "student": {
                    "studentId": "209900001",
                    "name": "Sarah Mansour",
                    "email": "sarah@zu.edu.jo",
                    "faculty": "Information Technology",
                    "major": "Artificial Intelligence",
                    "degree": "Bachelor",
                    "studyType": "Regular",
                    "admissionYear": 2022,
                    "academicAdvisor": "Dr. Advisor",
                    "academicStatus": "good",
                    "gpa": 88.5,
                    "gpaScale": 100,
                    "earnedCredits": 60,
                    "planKey": "ZU:IT:AI:P12",
                    "planNumber": "12",
                    "facultyCode": "IT",
                    "majorCode": "AI",
                },
            })
        if path == "/api/integrations/morshidi/v1/student/grades":
            return httpx.Response(200, json={
                "success": True,
                "cumulativeGpa": 88.5,
                "gpaScale": 100,
                "gradingPolicy": {
                    "version": "FAKE_UNIVERSITY_GRADING_POLICY_V1",
                    "gpa": {"numericMin": 0, "numericMax": 100, "scale": 100},
                    "courseGrade": {"numericMin": 0, "numericMax": 100},
                },
                "semesters": [
                    {
                        "term": "2025-1",
                        "termLabel": "Fall 2025",
                        "registeredHours": 15,
                        "passedHours": 15,
                        "semesterGpa": 88.5,
                        "cumulativeGpa": 88.5,
                        "courses": [
                            {
                                "courseCode": "CS101",
                                "name": "Programming 1",
                                "credits": 3,
                                "grade": 90,
                                "letterGrade": "A",
                                "status": "passed",
                            }
                        ],
                    }
                ],
            })
        if path == "/api/integrations/morshidi/v1/student/enrollments":
            return httpx.Response(200, json={
                "success": True,
                "term": "2026-1",
                "termLabel": "Fall 2026",
                "enrollments": [
                    {
                        "courseCode": "AI201",
                        "courseName": "Artificial Intelligence Concepts",
                        "sectionId": "AI201-01",
                        "sectionNumber": 1,
                        "credits": 3,
                        "days": "MW",
                        "daysArray": ["M", "W"],
                        "startTime": "09:30",
                        "endTime": "11:00",
                        "room": "IT-101",
                        "instructor": "Dr. Instructor",
                    }
                ],
            })
        if path in {"/v1/calendar", "/calendar/current"}:
            return httpx.Response(200, json={"code": "2026-1", "name_ar": "الفصل الأول 2026"})
        if path in {"/v1/offerings", "/offerings"}:
            return httpx.Response(200, json=[
                {
                    "section_id": "AI201-01",
                    "course_code": "AI201",
                    "capacity": 30,
                    "enrolled": 25,
                    "available": 5,
                    "status": "OPEN",
                }
            ])
        return httpx.Response(404, json={"detail": f"Not found: {path}"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(mock_fake_uni_handler)) as client:
        contract_client = UniversityContractClient(
            client=client,
            base_url="https://fake-university-aqdn.onrender.com",
        )
        adapter = FakeUniversityAdapter(
            contract_client,
            http_client=client,
            base_url="https://fake-university-aqdn.onrender.com",
        )

        health = await SISContractTestKit.verify_health_check(adapter)
        assert health.status == "HEALTHY"
        assert health.connectivity is True
        assert health.details.get("cursor") == 9

        profile = await SISContractTestKit.verify_student_profile(adapter, "209900001", "mock-token")
        assert profile.full_name == "Sarah Mansour"
        assert profile.cumulative_gpa == Decimal("88.5")

        grades = await SISContractTestKit.verify_grades(adapter, "209900001", "mock-token")
        assert len(grades) == 1
        assert grades[0].course_code == "CS101"
        assert grades[0].outcome == "PASSED"

        enrollments = await SISContractTestKit.verify_enrollments(adapter, "209900001", "mock-token")
        assert len(enrollments) == 1
        assert enrollments[0].course_code == "AI201"

        terms = await SISContractTestKit.verify_terms(adapter)
        assert len(terms) == 1
        assert terms[0].term_code == "2026-1"

        offerings = await SISContractTestKit.verify_offerings(adapter, "2026-1")
        assert len(offerings) == 1
        assert offerings[0].section_id == "AI201-01"
        assert offerings[0].available == 5

