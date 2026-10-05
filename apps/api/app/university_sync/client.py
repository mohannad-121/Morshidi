"""HTTP contract client for the Fake University integration and legacy offerings provider."""

from __future__ import annotations

import json
import logging
from datetime import datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from pydantic import TypeAdapter, ValidationError

from app.core.config import settings
from app.offerings.models import MeetingBlock, Modality, OfferingSection, OfferingSnapshot, SourceType
from app.offerings.provider import CourseOfferingProvider, OfferingProviderUnavailable
from app.university_sync.errors import (
    InvalidUniversityCredentialsError,
    UniversityProtocolError,
    UniversityRateLimitedError,
    UniversityUnavailableError,
)
from app.university_sync.models import (
    UniversityAcademicPlan,
    UniversityAcademicPlanResponse,
    UniversityCourse,
    UniversityCoursesPayload,
    UniversityCoursesResponse,
    UniversityEnrollmentRecord,
    UniversityEnrollmentsResponse,
    UniversityGradeRecord,
    UniversityGradesResponse,
    UniversityLoginResponse,
    UniversitySemesterGrades,
    UniversityStudentProfile,
    UniversityStudentResponse,
)

logger = logging.getLogger(__name__)

_GRADE_STATUS_TO_OUTCOME = {
    "passed": "PASSED",
    "failed": "FAILED",
    "withdrawn": "WITHDRAWN",
}


class UniversityContractClient:
    """Production client communicating with the external Fake University integration endpoints."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self._client = client
        self._base_url = base_url
        self._client_id = client_id
        self._client_secret = client_secret

    def _get_base_url(self) -> str:
        url = self._base_url or settings.uni_base_url or "https://fake-university-aqdn.onrender.com"
        return url.rstrip("/")

    def _get_client_id(self) -> str:
        return self._client_id or settings.uni_client_id or "morshidi"

    def _get_client_secret(self) -> str:
        if self._client_secret:
            return self._client_secret
        if settings.uni_client_secret:
            return settings.uni_client_secret.get_secret_value()
        return ""

    async def authenticate_student(self, student_id: str, password: str) -> UniversityLoginResponse:
        """Authenticate student credentials against Fake University.

        Transmits X-Morshidi-Client-Id and X-Morshidi-Client-Secret headers.
        Password exists only in transient process memory and is never logged or stored.
        """
        secret = self._get_client_secret()
        if not secret:
            raise UniversityUnavailableError("UNI_CLIENT_SECRET is not configured")

        url = f"{self._get_base_url()}/api/integrations/morshidi/v1/auth/login"
        headers = {
            "X-Morshidi-Client-Id": self._get_client_id(),
            "X-Morshidi-Client-Secret": secret,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {"studentId": student_id, "password": password}

        try:
            response = await self._client.post(url, headers=headers, json=payload, timeout=10)
        except (httpx.TimeoutException, httpx.NetworkError) as err:
            raise UniversityUnavailableError(f"University authentication request timed out: {err}") from err
        except httpx.HTTPError as err:
            raise UniversityUnavailableError(f"University authentication network error: {err}") from err

        if response.status_code == 401:
            raise InvalidUniversityCredentialsError("Invalid university credentials")
        if response.status_code == 429:
            retry_after = None
            raw_retry = response.headers.get("Retry-After")
            if raw_retry and raw_retry.isdigit():
                retry_after = int(raw_retry)
            raise UniversityRateLimitedError("University rate limit exceeded", retry_after=retry_after)
        if response.status_code >= 500:
            raise UniversityUnavailableError(f"University service unavailable (HTTP {response.status_code})")
        if response.status_code != 200:
            raise UniversityUnavailableError(f"Unexpected university authentication response (HTTP {response.status_code})")

        try:
            data = response.json()
            return UniversityLoginResponse.model_validate(data)
        except (json.JSONDecodeError, ValidationError, ValueError) as err:
            raise UniversityProtocolError(f"Malformed university authentication response: {err}") from err

    async def _get_authorized(self, path: str, token: str) -> Any:
        url = f"{self._get_base_url()}{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        try:
            response = await self._client.get(url, headers=headers, timeout=10)
        except (httpx.TimeoutException, httpx.NetworkError) as err:
            raise UniversityUnavailableError(f"University endpoint {path} timed out: {err}") from err
        except httpx.HTTPError as err:
            raise UniversityUnavailableError(f"University endpoint {path} network error: {err}") from err

        if response.status_code == 401:
            raise InvalidUniversityCredentialsError("University integration token invalid or expired")
        if response.status_code == 429:
            retry_after = None
            raw_retry = response.headers.get("Retry-After")
            if raw_retry and raw_retry.isdigit():
                retry_after = int(raw_retry)
            raise UniversityRateLimitedError("University rate limit exceeded", retry_after=retry_after)
        if response.status_code >= 500:
            raise UniversityUnavailableError(f"University service unavailable (HTTP {response.status_code})")
        if response.status_code != 200:
            raise UniversityUnavailableError(f"Unexpected university response (HTTP {response.status_code})")

        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as err:
            raise UniversityProtocolError(f"Malformed university JSON response on {path}: {err}") from err

    @staticmethod
    def _unwrap_envelope(
        data: Any,
        *,
        payload_keys: tuple[str, ...],
    ) -> Any:
        """Validate generic envelope semantics and return one allowlisted payload."""
        if not isinstance(data, dict):
            raise UniversityProtocolError("Malformed university response envelope: expected a JSON object")

        if "success" in data:
            success = data["success"]
            if not isinstance(success, bool):
                raise UniversityProtocolError(
                    "Malformed university response envelope: success must be a boolean"
                )
            if not success:
                raise UniversityProtocolError("University response envelope reported failure")

        for key in payload_keys:
            if key not in data:
                continue
            return data[key]

        allowed = ", ".join(repr(key) for key in payload_keys)
        raise UniversityProtocolError(
            f"Malformed university response envelope: missing payload key; expected one of {allowed}"
        )

    async def get_student_me(self, token: str) -> UniversityStudentProfile:
        data = await self._get_authorized("/api/integrations/morshidi/v1/student/me", token)
        payload = self._unwrap_envelope(
            data,
            payload_keys=("student", "data", "profile"),
        )
        try:
            if "student" in data:
                response = UniversityStudentResponse.model_validate(data)
                student = response.student
                return UniversityStudentProfile(
                    student_id=student.student_id,
                    name=student.name,
                    email=student.email,
                    faculty=student.faculty,
                    major=student.major,
                    degree=student.degree,
                    admission_year=student.admission_year,
                    academic_status=student.academic_status,
                    academic_advisor=student.academic_advisor,
                    cumulative_gpa=student.gpa,
                    earned_credits=student.earned_credits,
                )
            return UniversityStudentProfile.model_validate(payload)
        except (ValidationError, ValueError) as err:
            raise UniversityProtocolError(f"Malformed university student profile: {err}") from err

    async def get_student_courses(self, token: str) -> list[UniversityCourse]:
        data = await self._get_authorized("/api/integrations/morshidi/v1/student/courses", token)
        payload = self._unwrap_envelope(
            data,
            payload_keys=("courses", "data"),
        )
        try:
            if "courses" in data:
                response = UniversityCoursesResponse.model_validate(data)
                return self._flatten_grouped_courses(response.courses)
            return TypeAdapter(list[UniversityCourse]).validate_python(payload)
        except (ValidationError, ValueError) as err:
            raise UniversityProtocolError(f"Malformed university courses: {err}") from err

    @staticmethod
    def _flatten_grouped_courses(payload: UniversityCoursesPayload) -> list[UniversityCourse]:
        """Flatten real course groups deterministically without duplicates."""
        flattened: list[UniversityCourse] = []
        seen_codes: set[str] = set()
        groups = (
            ("completed", "completed", payload.completed),
            ("current", "enrolled", payload.current),
            ("remaining", "remaining", payload.remaining),
        )
        for group_name, expected_status, courses in groups:
            for course in courses:
                if course.status != expected_status:
                    raise ValueError(
                        f"course status {course.status!r} contradicts group {group_name!r}"
                    )
                if course.course_code in seen_codes:
                    raise ValueError(f"duplicate courseCode {course.course_code!r} across course groups")
                seen_codes.add(course.course_code)
                flattened.append(
                    UniversityCourse(
                        course_code=course.course_code,
                        title=course.name,
                        credit_hours=course.credits,
                        status=course.status,
                    )
                )
        return flattened

    async def get_student_grades(self, token: str) -> list[UniversityGradeRecord]:
        data = await self._get_authorized("/api/integrations/morshidi/v1/student/grades", token)
        payload = self._unwrap_envelope(
            data,
            payload_keys=("semesters", "grades", "data"),
        )
        try:
            if "semesters" in data:
                response = UniversityGradesResponse.model_validate(data)
                return self._flatten_semester_grades(response.semesters)
            return TypeAdapter(list[UniversityGradeRecord]).validate_python(payload)
        except (ValidationError, ValueError) as err:
            raise UniversityProtocolError(f"Malformed university grades: {err}") from err

    @staticmethod
    def _flatten_semester_grades(
        semesters: list[UniversitySemesterGrades],
    ) -> list[UniversityGradeRecord]:
        """Map each real nested course result to one existing attempt record."""
        return [
            UniversityGradeRecord(
                course_code=course.course_code,
                course_name=course.name,
                term=semester.term,
                letter_grade=course.letter_grade,
                numeric_grade=course.grade,
                credit_hours=course.credits,
                status=_GRADE_STATUS_TO_OUTCOME[course.status],
            )
            for semester in semesters
            for course in semester.courses
        ]

    async def get_student_enrollments(self, token: str) -> list[UniversityEnrollmentRecord]:
        data = await self._get_authorized("/api/integrations/morshidi/v1/student/enrollments", token)
        payload = self._unwrap_envelope(
            data,
            payload_keys=("enrollments", "data"),
        )
        try:
            if "enrollments" in data:
                response = UniversityEnrollmentsResponse.model_validate(data)
                return [
                    UniversityEnrollmentRecord(
                        course_code=enrollment.course_code,
                        course_name=enrollment.course_name,
                        section_id=enrollment.section_id,
                        term=response.term,
                        credit_hours=enrollment.credits,
                        instructor=enrollment.instructor,
                    )
                    for enrollment in response.enrollments
                ]
            return TypeAdapter(list[UniversityEnrollmentRecord]).validate_python(payload)
        except (ValidationError, ValueError) as err:
            raise UniversityProtocolError(f"Malformed university enrollments: {err}") from err

    async def get_student_academic_plan(self, token: str) -> UniversityAcademicPlan:
        data = await self._get_authorized("/api/integrations/morshidi/v1/student/academic-plan", token)
        payload = self._unwrap_envelope(
            data,
            payload_keys=("plan", "academicPlan", "data"),
        )
        try:
            if "plan" in data:
                response = UniversityAcademicPlanResponse.model_validate(data)
                plan = response.plan
                return UniversityAcademicPlan(
                    plan_id=plan.plan_id,
                    major=plan.major,
                    total_credit_hours=plan.total_required_credits,
                    courses=[course.model_dump(by_alias=True) for course in plan.courses],
                )
            return UniversityAcademicPlan.model_validate(payload)
        except (ValidationError, ValueError) as err:
            raise UniversityProtocolError(f"Malformed university academic plan: {err}") from err

    # ==========================================================================
    # Legacy methods for offering provider compatibility
    # ==========================================================================

    def _configured(self) -> tuple[str, str]:
        base = (self._base_url or settings.uni_base_url or "").rstrip("/")
        key = settings.uni_service_key.get_secret_value() if settings.uni_service_key else ""
        if not base or not key:
            raise OfferingProviderUnavailable("University source is not configured")
        return base, key

    async def get_json(self, path: str) -> Any:
        base, key = self._configured()
        try:
            response = await self._client.get(
                f"{base}{path}", headers={"X-Uni-Api-Key": key, "Accept": "application/json"}, timeout=5
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise OfferingProviderUnavailable("University source is unavailable") from error

    async def load_student(self, student_id: str) -> dict[str, Any]:
        return await self.get_json(f"/v1/integration/students/{student_id}")

    async def current_term(self) -> dict[str, Any]:
        return await self.get_json("/v1/calendar")

    async def manifest(self) -> dict[str, Any]:
        result = await self.get_json("/v1/manifest")
        return result if isinstance(result, dict) else {}

    async def live_offerings(self, term_code: str) -> list[dict[str, Any]]:
        result = await self.get_json(f"/v1/offerings?term={term_code}")
        if not isinstance(result, list):
            raise OfferingProviderUnavailable("University contract returned invalid offerings")
        return result

    async def resolve_period(self, period_id: str, term_code: str) -> dict[str, Any] | None:
        if not settings.supabase_url or not settings.supabase_secret_key or not settings.uni_university_id:
            raise OfferingProviderUnavailable("University period mapping is not configured")
        try:
            UUID(period_id)
            UUID(settings.uni_university_id)
        except ValueError as error:
            raise OfferingProviderUnavailable("University period mapping is invalid") from error
        headers = {
            "apikey": settings.supabase_secret_key.get_secret_value(),
            "Authorization": f"Bearer {settings.supabase_secret_key.get_secret_value()}",
        }
        params = {
            "id": f"eq.{period_id}",
            "period_key": f"eq.{term_code}",
            "select": "id,period_key,source_version",
            "limit": "1",
        }
        try:
            response = await self._client.get(
                f"{settings.supabase_url.rstrip('/')}/rest/v1/mock_registration_target_periods",
                headers=headers,
                params=params,
                timeout=5,
            )
            response.raise_for_status()
            rows = response.json()
            return rows[0] if isinstance(rows, list) and rows else None
        except (httpx.HTTPError, ValueError) as error:
            raise OfferingProviderUnavailable("University period mapping lookup failed") from error

    async def snapshot(self, period_id: str, term_code: str) -> OfferingSnapshot:
        period_row = await self.resolve_period(period_id, term_code)
        if period_row is None:
            raise OfferingProviderUnavailable("University target period is not configured")
        manifest_payload = await self.manifest()
        raw_sections = await self.live_offerings(term_code)
        sections = tuple(self._parse_section(row) for row in raw_sections)
        source_version = str(period_row.get("source_version") or manifest_payload.get("schema_version") or "uni-v1")
        now = datetime.now(timezone.utc)
        synthetic = bool(manifest_payload.get("synthetic", False))
        source_type = SourceType.SYNTHETIC if synthetic else SourceType.INSTITUTIONAL
        provenance = "SYNTHETIC_CONTRACT_FACT" if synthetic else "OFFICIAL_UNIVERSITY_FACT"
        return OfferingSnapshot(
            university_id=settings.uni_university_id,
            period_key=term_code,
            snapshot_id=f"snap-{period_id}",
            source_version=source_version,
            source_type=source_type,
            source_at=now,
            fresh_until=now + timedelta(days=1),
            complete=True,
            sections=sections,
            provenance=provenance,
        )

    def _parse_section(self, row: dict[str, Any]) -> OfferingSection:
        course_code = str(row.get("course_code") or "").strip()
        section_id = str(row.get("id") or "").strip()
        if not course_code or not section_id:
            raise OfferingProviderUnavailable("University section payload is missing required identifiers")
        status = "OPEN" if row.get("status") in {"متاحة", "open", "OPEN"} else "CLOSED"
        capacity = int(row.get("capacity") or 0)
        enrolled = int(row.get("enrolled") or 0)
        available = max(0, capacity - enrolled)
        day_map = {
            "الأحد": 7, "الاحد": 7, "sunday": 7,
            "الإثنين": 1, "الاثنين": 1, "monday": 1,
            "الثلاثاء": 2, "tuesday": 2,
            "الأربعاء": 3, "الاربعاء": 3, "wednesday": 3,
            "الخميس": 4, "thursday": 4,
            "الجمعة": 5, "friday": 5,
            "السبت": 6, "saturday": 6,
        }
        days_raw = row.get("days_array") or []
        meetings = []
        for d in days_raw:
            day_num = day_map.get(str(d).strip(), 7)
            start_raw = str(row.get("start_time") or "08:00")
            end_raw = str(row.get("end_time") or "09:30")
            meetings.append(
                MeetingBlock(
                    day=day_num,
                    starts_at=self._parse_time(start_raw),
                    ends_at=self._parse_time(end_raw),
                    timezone="Asia/Amman",
                )
            )
        if not meetings:
            meetings.append(
                MeetingBlock(
                    day=7,
                    starts_at=time(8, 0),
                    ends_at=time(9, 30),
                    timezone="Asia/Amman",
                )
            )
        return OfferingSection(
            section_id=section_id,
            course_code=course_code,
            status=status,
            modality=Modality.IN_PERSON,
            campus=None,
            location=None,
            meetings=tuple(meetings),
            capacity=capacity,
            enrolled=enrolled,
            available=available,
            waitlist=None,
            provenance="UNIVERSITY_CONTRACT",
            student_visible=True,
        )

    @staticmethod
    def _parse_time(raw: str) -> time:
        parts = [int(p) for p in raw.split(":")[:2]]
        return time(hour=parts[0], minute=parts[1] if len(parts) > 1 else 0)


class HttpUniversityOfferingProvider(CourseOfferingProvider):
    def __init__(self, client: UniversityContractClient, university_id: str | None = None) -> None:
        self._client = client
        self._university_id = university_id

    async def load_snapshot(self, university_id: str, period_id: str) -> OfferingSnapshot | None:
        if self._university_id and university_id != self._university_id:
            return None
        calendar = await self._client.current_term()
        term_code = str(calendar.get("currentTerm", {}).get("code", "")).strip()
        if not term_code:
            return None
        return await self._client.snapshot(period_id, term_code)

    async def active_term_offerings(self, period_id: str, term_code: str) -> OfferingSnapshot:
        return await self._client.snapshot(period_id, term_code)
