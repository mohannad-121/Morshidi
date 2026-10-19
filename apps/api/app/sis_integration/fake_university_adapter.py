"""Reference SIS adapter wrapping Fake University under the generic SISAdapter contract."""

from __future__ import annotations

from decimal import Decimal
from time import perf_counter
from typing import Any

import httpx

from app.university_sync.client import UniversityContractClient
from app.university_sync.errors import (
    InvalidUniversityCredentialsError,
    UniversityRateLimitedError,
    UniversityUnavailableError,
)

from .adapter_interface import SISAdapter
from .capabilities import SISCapability
from .errors import (
    SISAuthFailedError,
    SISRateLimitedError,
    SISUnavailableError,
)
from .models import (
    ChangeBatch,
    HealthResult,
    NormalizedAuthResult,
    NormalizedCourse,
    NormalizedEnrollment,
    NormalizedGradeAttempt,
    NormalizedOffering,
    NormalizedStudent,
    NormalizedStudyPlan,
    NormalizedTerm,
)

FAKE_UNIVERSITY_CAPABILITIES: set[SISCapability] = {
    SISCapability.IDENTITY_AUTH,
    SISCapability.STUDENT_PROFILE_READ,
    SISCapability.GRADES_READ,
    SISCapability.ENROLLMENTS_READ,
    SISCapability.CURRICULUM_READ,
    SISCapability.OFFERINGS_READ,
    SISCapability.REGISTRATION_PREVIEW,
    SISCapability.REGISTRATION_WRITE,
    SISCapability.DROP_WRITE,
    SISCapability.SECTION_CAPACITY,
    SISCapability.INCREMENTAL_SYNC,
    SISCapability.WEBHOOKS,
}


class FakeUniversityAdapter:
    """Official reference/sandbox implementation of the SISAdapter contract."""

    def __init__(
        self,
        contract_client: UniversityContractClient,
        *,
        http_client: httpx.AsyncClient | None = None,
        base_url: str | None = None,
    ) -> None:
        self._client = contract_client
        self._http = http_client or getattr(contract_client, "_client", httpx.AsyncClient())
        self._base_url = (base_url or contract_client._get_base_url()).rstrip("/")

    @property
    def provider_type(self) -> str:
        return "fake_university"

    @property
    def capabilities(self) -> set[SISCapability]:
        return FAKE_UNIVERSITY_CAPABILITIES

    async def health_check(self) -> HealthResult:
        start = perf_counter()
        try:
            resp = await self._http.get(f"{self._base_url}/healthz", timeout=5)
            elapsed_ms = round((perf_counter() - start) * 1000, 2)
            if resp.status_code == 200:
                data = resp.json()
                return HealthResult(
                    status="HEALTHY",
                    connectivity=True,
                    latency_ms=elapsed_ms,
                    details={"cursor": data.get("cursor"), "ready": data.get("ready")},
                )
            return HealthResult(
                status="DEGRADED",
                connectivity=True,
                latency_ms=elapsed_ms,
                details={"http_status": resp.status_code},
            )
        except Exception as err:
            elapsed_ms = round((perf_counter() - start) * 1000, 2)
            return HealthResult(
                status="UNHEALTHY",
                connectivity=False,
                latency_ms=elapsed_ms,
                details={"error": str(err)},
            )

    async def authenticate_student(self, student_id: str, password: str) -> NormalizedAuthResult:
        try:
            res = await self._client.authenticate_student(student_id, password)
            return NormalizedAuthResult(
                authenticated=True,
                university_student_id=res.student_id or student_id,
                token=res.token,
                full_name=res.student_name,
                metadata={"plan_number": res.study_plan_number, "plan_key": res.plan_key},
            )
        except InvalidUniversityCredentialsError as err:
            raise SISAuthFailedError("Invalid student credentials") from err
        except UniversityRateLimitedError as err:
            raise SISRateLimitedError("Rate limit exceeded", retry_after=err.retry_after) from err
        except UniversityUnavailableError as err:
            raise SISUnavailableError(str(err)) from err

    async def get_student_profile(self, student_id: str, token: str) -> NormalizedStudent:
        try:
            p = await self._client.get_student_me(token)
            return NormalizedStudent(
                university_student_id=p.student_id,
                full_name=p.name,
                email=p.email,
                faculty_code=p.faculty_code,
                major_code=p.major_code,
                plan_key=p.plan_key,
                plan_number=getattr(p, "plan_number", None) or getattr(p, "study_plan", None),
                academic_standing=getattr(p, "academic_standing", None) or getattr(p, "academic_status", None),
                cumulative_gpa=Decimal(str(p.cumulative_gpa)) if getattr(p, "cumulative_gpa", None) is not None else None,
                gpa_scale=Decimal(str(p.gpa_scale)) if getattr(p, "gpa_scale", None) is not None else None,
                earned_credit_hours=Decimal(str(getattr(p, "earned_credit_hours", None) or getattr(p, "earned_credits", None))) if (getattr(p, "earned_credit_hours", None) is not None or getattr(p, "earned_credits", None) is not None) else None,
                registered_credit_hours=Decimal(str(getattr(p, "registered_credit_hours", None) or getattr(p, "registered_credits", None))) if (getattr(p, "registered_credit_hours", None) is not None or getattr(p, "registered_credits", None) is not None) else None,
                raw_payload=p.model_dump(mode="json"),
            )
        except Exception as err:
            raise SISUnavailableError(f"Failed to fetch profile: {err}") from err

    async def get_current_courses(self, student_id: str, token: str) -> list[NormalizedCourse]:
        try:
            courses = await self._client.get_student_courses(token)
            result: list[NormalizedCourse] = []
            for c in courses:
                result.append(NormalizedCourse(
                    course_code=c.course_code,
                    name_ar=c.course_name_ar,
                    name_en=c.course_name_en,
                    credit_hours=Decimal(str(c.credit_hours)),
                    raw_payload=c.model_dump(mode="json"),
                ))
            return result
        except Exception as err:
            raise SISUnavailableError(f"Failed to fetch current courses: {err}") from err

    async def get_grades(self, student_id: str, token: str) -> list[NormalizedGradeAttempt]:
        try:
            snapshot = await self._client.get_student_grades(token)
            result: list[NormalizedGradeAttempt] = []
            for r in snapshot.records:
                status_raw = str(getattr(r, "status", None) or getattr(r, "grade_status", "passed")).lower()
                outcome = "PASSED" if status_raw in {"passed", "pass"} else "FAILED" if status_raw in {"failed", "fail"} else "WITHDRAWN" if status_raw in {"withdrawn", "w"} else "IN_PROGRESS"
                term_val = str(getattr(r, "term", None) or getattr(r, "term_id", "") or "CURRENT")
                result.append(NormalizedGradeAttempt(
                    course_code=r.course_code,
                    term_code=term_val,
                    outcome=outcome,
                    numeric_grade=Decimal(str(r.numeric_grade)) if getattr(r, "numeric_grade", None) is not None else None,
                    letter_grade=r.letter_grade,
                    credit_hours=Decimal(str(r.credit_hours)) if getattr(r, "credit_hours", None) is not None else None,
                    is_official=True,
                    attempt_sequence=int(getattr(r, "attempt_sequence", 1) or 1),
                    raw_payload=r.model_dump(mode="json"),
                ))
            return result
        except Exception as err:
            raise SISUnavailableError(f"Failed to fetch grades: {err}") from err

    async def get_enrollments(self, student_id: str, token: str) -> list[NormalizedEnrollment]:
        try:
            enrollments = await self._client.get_student_enrollments(token)
            result: list[NormalizedEnrollment] = []
            for e in enrollments:
                sec_code = str(getattr(e, "section_id", None) or getattr(e, "section_code", "") or "1")
                term_val = str(getattr(e, "term", None) or getattr(e, "semester_id", "") or "CURRENT")
                credits_val = Decimal(str(getattr(e, "credit_hours", 3) or 3))
                result.append(NormalizedEnrollment(
                    course_code=e.course_code,
                    section_code=sec_code,
                    term_code=term_val,
                    status="ENROLLED",
                    credit_hours=credits_val,
                    raw_payload=e.model_dump(mode="json"),
                ))
            return result
        except Exception as err:
            raise SISUnavailableError(f"Failed to fetch enrollments: {err}") from err

    async def get_academic_plan(self, student_id: str, token: str) -> NormalizedStudyPlan:
        try:
            plan = await self._client.get_student_academic_plan(token)
            return NormalizedStudyPlan(
                plan_key=plan.plan_key or f"ZU:{plan.faculty_code}:{plan.major_code}:P{plan.plan_number or '12'}",
                plan_number=plan.plan_number or plan.plan_id,
                faculty_code=plan.faculty_code,
                major_code=plan.major_code,
                total_credit_hours=Decimal(str(plan.total_credit_hours)),
                required_courses=[c.course_code for c in plan.courses],
                raw_payload=plan.model_dump(mode="json"),
            )
        except Exception as err:
            raise SISUnavailableError(f"Failed to fetch academic plan: {err}") from err

    async def get_terms(self) -> list[NormalizedTerm]:
        try:
            resp = await self._http.get(f"{self._base_url}/v1/calendar")
            cal = resp.json() if resp.status_code == 200 else {}
            code = cal.get("code") or cal.get("currentTerm") or "CURRENT"
            name = cal.get("name_ar") or cal.get("term_name_ar") or "الفصل الحالي"
            return [NormalizedTerm(term_code=str(code), term_name_ar=str(name), is_current=True, is_registration_open=True)]
        except Exception as err:
            raise SISUnavailableError(f"Failed to fetch terms: {err}") from err

    async def get_course_offerings(self, term_code: str) -> list[NormalizedOffering]:
        try:
            resp = await self._http.get(f"{self._base_url}/v1/offerings", params={"term": term_code})
            raw = resp.json() if resp.status_code == 200 else []
            result: list[NormalizedOffering] = []
            for r in raw:
                if not isinstance(r, dict):
                    continue
                code = str(r.get("course_code") or r.get("courseCode") or "")
                sec_id = str(r.get("id") or r.get("section_id") or "")
                cap = int(r.get("capacity") or 30)
                enr = int(r.get("enrolled") or 0)
                avail = int(r.get("available") or max(0, cap - enr))
                result.append(NormalizedOffering(
                    section_id=sec_id,
                    course_code=code,
                    term_code=term_code,
                    capacity=cap,
                    enrolled=enr,
                    available=avail,
                    status=str(r.get("status") or "OPEN"),
                    raw_payload=r,
                ))
            return result
        except Exception as err:
            raise SISUnavailableError(f"Failed to fetch offerings: {err}") from err

    async def get_registration_context(self, student_id: str, token: str) -> dict[str, Any]:
        return await self._client.registration_request(
            "GET", "/api/integrations/morshidi/v1/student/registration/context", token
        )

    async def preview_registration(
        self, student_id: str, token: str, section_ids: list[str]
    ) -> dict[str, Any]:
        return await self._client.registration_request(
            "POST", "/api/integrations/morshidi/v1/student/registration/preview", token,
            payload={"sectionIds": section_ids},
        )

    async def register_sections(
        self, student_id: str, token: str, section_ids: list[str], idempotency_key: str
    ) -> dict[str, Any]:
        return await self._client.registration_request(
            "POST", "/api/integrations/morshidi/v1/student/registration/register", token,
            payload={"sectionIds": section_ids}, idempotency_key=idempotency_key,
        )

    async def drop_sections(
        self, student_id: str, token: str, section_id: str, idempotency_key: str
    ) -> dict[str, Any]:
        return await self._client.registration_request(
            "POST", "/api/integrations/morshidi/v1/student/registration/drop", token,
            payload={"sectionId": section_id}, idempotency_key=idempotency_key,
        )

    async def get_cursor_or_change_token(self) -> str | None:
        try:
            resp = await self._http.get(f"{self._base_url}/healthz", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                cur = data.get("cursor")
                return str(cur) if cur is not None else None
            return None
        except Exception:
            return None

    async def fetch_changes_since(self, cursor: str | None) -> ChangeBatch:
        # In Fake University reference SIS, cursor is monotonic version counter
        cur = await self.get_cursor_or_change_token()
        return ChangeBatch(cursor=cur, has_more=False)
