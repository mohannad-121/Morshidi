"""GET-only Supabase adapter for persisted student academic state."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

import httpx

from app.rules.models import AttemptOutcome, StudentCourseAttempt
from app.student.errors import (
    StudentProfileIntegrityError,
    StudentProfileNotFound,
    StudentProfileTransportError,
)
from app.student.models import StudentAcademicState


class SupabaseStudentAcademicRepository:
    """Server-side, read-only owner-scoped student state adapter.

    Attempts are ordered by persisted ``created_at`` then ``id``. The server
    key is only sent as an API-key header and is never retained in errors.
    """

    def __init__(self, supabase_url: str, server_key: str, client: httpx.AsyncClient | None = None) -> None:
        if not supabase_url.strip() or not server_key.strip():
            raise ValueError("supabase_url and server_key must not be empty")
        self._rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._server_key = server_key
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def load_student_academic_state(self, owner_user_id: UUID | str) -> StudentAcademicState:
        owner_id = str(owner_user_id)
        profiles = await self._get_rows(
            "student_academic_profiles",
            {
                "select": "id,owner_user_id,study_plan_id,reported_cumulative_gpa,reported_gpa_scale,reported_earned_credit_hours",
                "owner_user_id": f"eq.{owner_id}",
            },
        )
        if not profiles:
            raise StudentProfileNotFound("Student academic profile was not found")
        if len(profiles) != 1:
            raise StudentProfileIntegrityError("Multiple student profiles matched one owner")
        profile = profiles[0]
        profile_id = _uuid_text(profile, "id", "profile")
        if _uuid_text(profile, "owner_user_id", "profile") != owner_id:
            raise StudentProfileIntegrityError("Profile response did not match requested owner")
        attempts = await self._get_rows(
            "student_course_attempts",
            {
                "select": "id,profile_id,outcome,created_at,courses(course_code)",
                "profile_id": f"eq.{profile_id}",
                "order": "created_at.asc,id.asc",
            },
        )
        mapped: list[StudentCourseAttempt] = []
        for row in attempts:
            if _uuid_text(row, "profile_id", "attempt") != profile_id:
                raise StudentProfileIntegrityError("Attempt response belongs to another profile")
            course = row.get("courses")
            if not isinstance(course, Mapping):
                raise StudentProfileIntegrityError("Attempt is missing its referenced course")
            try:
                outcome = AttemptOutcome(_required_text(row, "outcome", "attempt"))
            except ValueError as error:
                raise StudentProfileIntegrityError("Attempt has unsupported outcome") from error
            mapped.append(StudentCourseAttempt(_required_text(course, "course_code", "course"), outcome))
        return StudentAcademicState(
            profile_id=profile_id,
            owner_user_id=owner_id,
            study_plan_id=_uuid_text(profile, "study_plan_id", "profile"),
            reported_cumulative_gpa=_decimal(profile.get("reported_cumulative_gpa"), "reported_cumulative_gpa"),
            reported_gpa_scale=_decimal(profile.get("reported_gpa_scale"), "reported_gpa_scale"),
            reported_earned_credit_hours=_decimal(profile.get("reported_earned_credit_hours"), "reported_earned_credit_hours"),
            attempts=tuple(mapped),
        )

    async def _get_rows(self, resource: str, params: Mapping[str, str]) -> list[Mapping[str, Any]]:
        try:
            response = await self._client.get(f"{self._rest_url}/{resource}", params=params, headers={"apikey": self._server_key, "Authorization": f"Bearer {self._server_key}", "Accept": "application/json"})
        except (httpx.TimeoutException, httpx.RequestError) as error:
            raise StudentProfileTransportError("GET", resource) from error
        if not 200 <= response.status_code < 300:
            raise StudentProfileTransportError("GET", resource, status_code=response.status_code)
        try:
            body = response.json()
        except ValueError as error:
            raise StudentProfileTransportError("decode response", resource) from error
        if not isinstance(body, list) or not all(isinstance(row, Mapping) for row in body):
            raise StudentProfileIntegrityError(f"{resource} response is not a row array")
        return list(body)


def _required_text(row: Mapping[str, Any], field: str, resource: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise StudentProfileIntegrityError(f"{resource} is missing required {field}")
    return value


def _uuid_text(row: Mapping[str, Any], field: str, resource: str) -> str:
    value = _required_text(row, field, resource)
    try:
        return str(UUID(value))
    except ValueError as error:
        raise StudentProfileIntegrityError(f"{resource} has invalid {field}") from error


def _decimal(value: Any, field: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise StudentProfileIntegrityError(f"profile has invalid {field}")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise StudentProfileIntegrityError(f"profile has invalid {field}") from error
