"""Configurable generic REST SIS adapter mapping arbitrary university endpoints to normalized DTOs."""

from __future__ import annotations

from decimal import Decimal
from time import perf_counter
from typing import Any

import httpx

from .adapter_interface import SISAdapter
from .capabilities import SISCapability
from .errors import (
    CapabilityNotSupportedError,
    SISAuthFailedError,
    SISProtocolError,
    SISRateLimitedError,
    SISTimeoutError,
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
    UniversityIntegrationConfig,
)
from .security import resolve_secret, validate_target_url

DEFAULT_GENERIC_REST_CAPABILITIES: set[SISCapability] = {
    SISCapability.IDENTITY_AUTH,
    SISCapability.STUDENT_PROFILE_READ,
    SISCapability.GRADES_READ,
    SISCapability.ENROLLMENTS_READ,
    SISCapability.CURRICULUM_READ,
    SISCapability.OFFERINGS_READ,
    SISCapability.SECTION_CAPACITY,
    SISCapability.INCREMENTAL_SYNC,
}


class GenericRestAdapter:
    """Configurable REST adapter for external university SIS APIs."""

    def __init__(
        self,
        config: UniversityIntegrationConfig,
        *,
        http_client: httpx.AsyncClient | None = None,
        allow_localhost: bool = False,
    ) -> None:
        self._config = config
        self._base_url = validate_target_url(config.base_url, allow_localhost=allow_localhost)
        connect_timeout = config.timeouts_ms.get("connect", 5000) / 1000.0
        read_timeout = config.timeouts_ms.get("read", 10000) / 1000.0
        self._timeout = httpx.Timeout(read_timeout, connect=connect_timeout)
        self._http = http_client or httpx.AsyncClient(timeout=self._timeout)
        self._capabilities = set(config.supported_capabilities) if config.supported_capabilities else DEFAULT_GENERIC_REST_CAPABILITIES

    @property
    def provider_type(self) -> str:
        return "generic_rest"

    @property
    def capabilities(self) -> set[SISCapability]:
        return self._capabilities

    def _get_auth_headers(self, token: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "User-Agent": "Morshidi-SIS-Gateway/1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        elif self._config.auth_method == "token":
            secret = resolve_secret(self._config.secret_env_ref)
            if secret:
                headers["Authorization"] = f"Bearer {secret}"
        elif self._config.auth_method == "client_credentials" and self._config.client_id:
            secret = resolve_secret(self._config.secret_env_ref)
            if secret:
                headers["X-API-Key"] = secret
                headers["X-Client-ID"] = self._config.client_id
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        headers = self._get_auth_headers(token)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
            headers["X-Idempotency-Key"] = idempotency_key

        try:
            resp = await self._http.request(
                method,
                url,
                params=params,
                json=payload,
                headers=headers,
            )
        except httpx.TimeoutException as err:
            raise SISTimeoutError(f"Request to SIS timed out: {err}") from err
        except httpx.NetworkError as err:
            raise SISUnavailableError(f"Network error contacting SIS: {err}") from err
        except Exception as err:
            raise SISUnavailableError(f"Error contacting SIS: {err}") from err

        if resp.status_code == 401 or resp.status_code == 403:
            raise SISAuthFailedError(f"SIS authentication failed (HTTP {resp.status_code})")
        if resp.status_code == 429:
            retry_after_hdr = resp.headers.get("Retry-After")
            retry_after = int(retry_after_hdr) if retry_after_hdr and retry_after_hdr.isdigit() else None
            raise SISRateLimitedError("SIS rate limit exceeded", retry_after=retry_after)
        if resp.status_code >= 500:
            raise SISUnavailableError(f"External SIS internal error (HTTP {resp.status_code})")
        if resp.status_code >= 400:
            raise SISProtocolError(f"SIS returned HTTP {resp.status_code}: {resp.text[:200]}")

        try:
            return resp.json()
        except Exception as err:
            raise SISProtocolError(f"Failed to parse SIS JSON response: {err}") from err

    async def health_check(self) -> HealthResult:
        start = perf_counter()
        try:
            resp = await self._http.get(
                f"{self._base_url}/health",
                headers=self._get_auth_headers(),
                timeout=5.0,
            )
            elapsed_ms = round((perf_counter() - start) * 1000, 2)
            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                return HealthResult(
                    status="HEALTHY",
                    connectivity=True,
                    latency_ms=elapsed_ms,
                    details=data if isinstance(data, dict) else {},
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
        if SISCapability.IDENTITY_AUTH not in self.capabilities:
            raise CapabilityNotSupportedError("IDENTITY_AUTH capability is not enabled for this adapter")
        data = await self._request("POST", "/auth/login", payload={"student_id": student_id, "password": password})
        if not isinstance(data, dict) or not data.get("authenticated", False):
            raise SISAuthFailedError("Authentication credentials rejected")
        return NormalizedAuthResult(
            authenticated=True,
            university_student_id=str(data.get("student_id") or student_id),
            token=data.get("token"),
            full_name=data.get("full_name") or data.get("name"),
            metadata=data.get("metadata", {}),
        )

    async def get_student_profile(self, student_id: str, token: str) -> NormalizedStudent:
        if SISCapability.STUDENT_PROFILE_READ not in self.capabilities:
            raise CapabilityNotSupportedError("STUDENT_PROFILE_READ capability is not enabled")
        data = await self._request("GET", f"/students/{student_id}", token=token)
        if not isinstance(data, dict):
            raise SISProtocolError("Expected dict payload for student profile")
        return NormalizedStudent(
            university_student_id=str(data.get("student_id") or student_id),
            full_name=data.get("full_name") or data.get("name"),
            email=data.get("email"),
            faculty_code=data.get("faculty_code") or data.get("faculty"),
            major_code=data.get("major_code") or data.get("major"),
            plan_key=data.get("plan_key"),
            plan_number=str(data.get("plan_number")) if data.get("plan_number") is not None else None,
            academic_standing=data.get("academic_standing"),
            cumulative_gpa=Decimal(str(data["cumulative_gpa"])) if data.get("cumulative_gpa") is not None else None,
            gpa_scale=Decimal(str(data["gpa_scale"])) if data.get("gpa_scale") is not None else None,
            earned_credit_hours=Decimal(str(data["earned_credit_hours"])) if data.get("earned_credit_hours") is not None else None,
            registered_credit_hours=Decimal(str(data["registered_credit_hours"])) if data.get("registered_credit_hours") is not None else None,
            raw_payload=data,
        )

    async def get_current_courses(self, student_id: str, token: str) -> list[NormalizedCourse]:
        data = await self._request("GET", f"/students/{student_id}/courses", token=token)
        items = data if isinstance(data, list) else data.get("courses", [])
        result: list[NormalizedCourse] = []
        for item in items:
            if isinstance(item, dict):
                result.append(NormalizedCourse(
                    course_code=str(item.get("course_code") or item.get("code") or ""),
                    name_ar=item.get("name_ar") or item.get("title_ar"),
                    name_en=item.get("name_en") or item.get("title_en"),
                    credit_hours=Decimal(str(item.get("credit_hours", 3))),
                    faculty_code=item.get("faculty_code"),
                    department_code=item.get("department_code"),
                    prerequisite_codes=item.get("prerequisite_codes", []),
                    raw_payload=item,
                ))
        return result

    async def get_grades(self, student_id: str, token: str) -> list[NormalizedGradeAttempt]:
        if SISCapability.GRADES_READ not in self.capabilities:
            raise CapabilityNotSupportedError("GRADES_READ capability is not enabled")
        data = await self._request("GET", f"/students/{student_id}/grades", token=token)
        items = data if isinstance(data, list) else data.get("grades", [])
        result: list[NormalizedGradeAttempt] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_outcome = str(item.get("outcome") or item.get("status") or "").upper()
            outcome = "PASSED" if raw_outcome in {"PASSED", "PASS"} else "FAILED" if raw_outcome in {"FAILED", "FAIL"} else "WITHDRAWN" if raw_outcome in {"WITHDRAWN", "W"} else "IN_PROGRESS"
            result.append(NormalizedGradeAttempt(
                course_code=str(item.get("course_code") or item.get("code") or ""),
                term_code=str(item.get("term_code") or item.get("term_id") or ""),
                outcome=outcome,
                numeric_grade=Decimal(str(item["numeric_grade"])) if item.get("numeric_grade") is not None else None,
                letter_grade=item.get("letter_grade"),
                credit_hours=Decimal(str(item["credit_hours"])) if item.get("credit_hours") is not None else None,
                is_official=bool(item.get("is_official", True)),
                attempt_sequence=int(item.get("attempt_sequence", 1)),
                raw_payload=item,
            ))
        return result

    async def get_enrollments(self, student_id: str, token: str) -> list[NormalizedEnrollment]:
        if SISCapability.ENROLLMENTS_READ not in self.capabilities:
            raise CapabilityNotSupportedError("ENROLLMENTS_READ capability is not enabled")
        data = await self._request("GET", f"/students/{student_id}/enrollments", token=token)
        items = data if isinstance(data, list) else data.get("enrollments", [])
        result: list[NormalizedEnrollment] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_status = str(item.get("status") or "ENROLLED").upper()
            status = "WAITLISTED" if raw_status == "WAITLISTED" else "DROPPED" if raw_status == "DROPPED" else "ENROLLED"
            result.append(NormalizedEnrollment(
                course_code=str(item.get("course_code") or item.get("code") or ""),
                section_code=str(item.get("section_code") or item.get("section_id") or ""),
                term_code=str(item.get("term_code") or item.get("semester_id") or ""),
                status=status,
                credit_hours=Decimal(str(item.get("credit_hours", 3))),
                raw_payload=item,
            ))
        return result

    async def get_academic_plan(self, student_id: str, token: str) -> NormalizedStudyPlan:
        if SISCapability.CURRICULUM_READ not in self.capabilities:
            raise CapabilityNotSupportedError("CURRICULUM_READ capability is not enabled")
        data = await self._request("GET", f"/students/{student_id}/academic-plan", token=token)
        if not isinstance(data, dict):
            raise SISProtocolError("Expected dict payload for academic plan")
        courses = data.get("required_courses") or [c.get("course_code") for c in data.get("courses", []) if isinstance(c, dict)]
        return NormalizedStudyPlan(
            plan_key=str(data.get("plan_key") or f"PLAN:{data.get('plan_id', 'DEFAULT')}"),
            plan_number=str(data.get("plan_number")) if data.get("plan_number") is not None else None,
            faculty_code=data.get("faculty_code"),
            major_code=data.get("major_code"),
            total_credit_hours=Decimal(str(data.get("total_credit_hours", 132))),
            required_courses=courses,
            raw_payload=data,
        )

    async def get_terms(self) -> list[NormalizedTerm]:
        data = await self._request("GET", "/terms")
        items = data if isinstance(data, list) else data.get("terms", [])
        result: list[NormalizedTerm] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            result.append(NormalizedTerm(
                term_code=str(item.get("term_code") or item.get("code") or ""),
                term_name_ar=str(item.get("term_name_ar") or item.get("name_ar") or item.get("term_code") or ""),
                term_name_en=item.get("term_name_en") or item.get("name_en"),
                start_date=item.get("start_date"),
                end_date=item.get("end_date"),
                is_current=bool(item.get("is_current", False)),
                is_registration_open=bool(item.get("is_registration_open", False)),
            ))
        return result

    async def get_course_offerings(self, term_code: str) -> list[NormalizedOffering]:
        if SISCapability.OFFERINGS_READ not in self.capabilities:
            raise CapabilityNotSupportedError("OFFERINGS_READ capability is not enabled")
        data = await self._request("GET", "/offerings", params={"term_code": term_code})
        items = data if isinstance(data, list) else data.get("offerings", [])
        result: list[NormalizedOffering] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            cap = int(item.get("capacity", 30))
            enr = int(item.get("enrolled", 0))
            avail = int(item.get("available", max(0, cap - enr)))
            result.append(NormalizedOffering(
                section_id=str(item.get("section_id") or item.get("id") or ""),
                course_code=str(item.get("course_code") or item.get("code") or ""),
                term_code=term_code,
                section_number=str(item.get("section_number", "1")),
                instructor_name=item.get("instructor_name"),
                capacity=cap,
                enrolled=enr,
                available=avail,
                status=str(item.get("status", "OPEN")),
                schedule_summary=item.get("schedule_summary"),
                raw_payload=item,
            ))
        return result

    async def get_registration_context(self, student_id: str, token: str) -> dict[str, Any]:
        return await self._request("GET", f"/students/{student_id}/registration-context", token=token)

    async def preview_registration(
        self, student_id: str, token: str, section_ids: list[str]
    ) -> dict[str, Any]:
        if SISCapability.REGISTRATION_PREVIEW not in self.capabilities:
            raise CapabilityNotSupportedError("REGISTRATION_PREVIEW capability is not enabled")
        return await self._request(
            "POST",
            f"/students/{student_id}/registration/preview",
            token=token,
            payload={"section_ids": section_ids},
        )

    async def register_sections(
        self, student_id: str, token: str, section_ids: list[str], idempotency_key: str
    ) -> dict[str, Any]:
        if SISCapability.REGISTRATION_WRITE not in self.capabilities:
            raise CapabilityNotSupportedError("REGISTRATION_WRITE capability is not enabled")
        return await self._request(
            "POST",
            f"/students/{student_id}/registration/register",
            token=token,
            payload={"section_ids": section_ids},
            idempotency_key=idempotency_key,
        )

    async def drop_sections(
        self, student_id: str, token: str, section_id: str, idempotency_key: str
    ) -> dict[str, Any]:
        if SISCapability.DROP_WRITE not in self.capabilities:
            raise CapabilityNotSupportedError("DROP_WRITE capability is not enabled")
        return await self._request(
            "POST",
            f"/students/{student_id}/registration/drop",
            token=token,
            payload={"section_id": section_id},
            idempotency_key=idempotency_key,
        )

    async def get_cursor_or_change_token(self) -> str | None:
        if SISCapability.INCREMENTAL_SYNC not in self.capabilities:
            return None
        try:
            data = await self._request("GET", "/sync/cursor")
            if isinstance(data, dict):
                return str(data.get("cursor") or "")
            return None
        except Exception:
            return None

    async def fetch_changes_since(self, cursor: str | None) -> ChangeBatch:
        if SISCapability.INCREMENTAL_SYNC not in self.capabilities:
            raise CapabilityNotSupportedError("INCREMENTAL_SYNC capability is not enabled")
        data = await self._request("GET", "/sync/changes", params={"cursor": cursor} if cursor else None)
        if not isinstance(data, dict):
            return ChangeBatch(cursor=cursor, has_more=False)
        return ChangeBatch(
            cursor=data.get("cursor"),
            has_more=bool(data.get("has_more", False)),
            students=[NormalizedStudent.model_validate(s) for s in data.get("students", []) if isinstance(s, dict)],
            grades=[NormalizedGradeAttempt.model_validate(g) for g in data.get("grades", []) if isinstance(g, dict)],
            enrollments=[NormalizedEnrollment.model_validate(e) for e in data.get("enrollments", []) if isinstance(e, dict)],
        )

