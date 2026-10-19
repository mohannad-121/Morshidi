"""Batched read-only Supabase repository for institutional aggregates."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Mapping
from typing import Any, Protocol

import httpx

from .models import AnalyticsSnapshot, CourseFact, ProgramFact, SectionFact, StudentFact


class InstitutionalAnalyticsRepository(Protocol):
    async def load_snapshot(
        self, university_id: str, term_key: str, *,
        sections: tuple[SectionFact, ...] | None = None,
        offering_version: str | None = None, offering_complete: bool = False,
        assigned_student_ids: frozenset[str] | None = None,
    ) -> AnalyticsSnapshot: ...

    async def load_assigned_student_ids(self, advisor_user_id: str, university_id: str) -> frozenset[str]: ...


class InstitutionalAnalyticsRepositoryError(RuntimeError):
    pass


class SupabaseInstitutionalAnalyticsRepository:
    """Loads one aggregate snapshot with bounded parallel requests, never one request per student."""

    def __init__(self, supabase_url: str, server_key: str, client: httpx.AsyncClient | None = None) -> None:
        if not supabase_url.strip() or not server_key.strip():
            raise ValueError("supabase_url and server_key are required")
        self._rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._server_key = server_key
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def load_assigned_student_ids(self, advisor_user_id: str, university_id: str) -> frozenset[str]:
        rows = await self._get("advisor_student_assignments", {
            "select": "student_user_id", "advisor_user_id": f"eq.{advisor_user_id}",
            "university_id": f"eq.{university_id}", "is_active": "eq.true",
        })
        return frozenset(str(row["student_user_id"]) for row in rows if row.get("student_user_id"))

    async def load_snapshot(
        self, university_id: str, term_key: str, *,
        sections: tuple[SectionFact, ...] | None = None,
        offering_version: str | None = None, offering_complete: bool = False,
        assigned_student_ids: frozenset[str] | None = None,
    ) -> AnalyticsSnapshot:
        plans_task = self._get("study_plans", {
            "select": "id,plan_number,total_credit_hours,status,updated_at,majors(id,code,name_ar,name_en,faculties(id,code,name_ar,name_en,university_id))",
            "status": "eq.active", "order": "id.asc",
        })
        courses_task = self._get("study_plan_courses", {
            "select": "id,study_plan_id,credit_hours,display_order,prerequisite_logic_status,verification_status,updated_at,courses(id,course_code,name_ar,name_en),requirement_groups(group_code,requirement_type,scope),course_dependency_groups(dependency_type,verification_status,course_dependency_options(verification_status,courses(course_code)))",
            "active": "eq.true", "order": "study_plan_id.asc,display_order.asc,id.asc",
        })
        profiles_task = self._get("student_academic_profiles", {
            "select": "id,owner_user_id,study_plan_id,reported_earned_credit_hours,updated_at",
            "order": "study_plan_id.asc,id.asc",
        })
        attempts_task = self._get("student_course_attempts", {
            "select": "profile_id,outcome,updated_at,courses(course_code)", "order": "profile_id.asc,created_at.asc,id.asc",
        })
        intents_task = self._get("mock_registration_intent_revisions", {
            "select": "owner_user_id,study_plan_id,revision,lifecycle_status,validation_status,created_at,mock_registration_target_periods(period_key),mock_registration_intent_courses(course_code)",
            "lifecycle_status": "eq.SUBMITTED", "validation_status": "eq.VALID",
            "order": "owner_user_id.asc,study_plan_id.asc,revision.desc",
        })
        plan_rows, course_rows, profile_rows, attempt_rows, intent_rows = await asyncio.gather(
            plans_task, courses_task, profiles_task, attempts_task, intents_task)

        programs: list[ProgramFact] = []
        plan_ids: set[str] = set()
        version_values: list[str] = []
        for row in plan_rows:
            major = row.get("majors")
            faculty = major.get("faculties") if isinstance(major, Mapping) else None
            if not isinstance(major, Mapping) or not isinstance(faculty, Mapping):
                continue
            if str(faculty.get("university_id")) != university_id:
                continue
            plan_id = str(row.get("id") or "")
            faculty_code = str(faculty.get("code") or "").strip()
            major_code = str(major.get("code") or "").strip()
            plan_number = str(row.get("plan_number") or "").strip()
            if not all((plan_id, faculty_code, major_code, plan_number)):
                raise InstitutionalAnalyticsRepositoryError("Catalog plan is missing composite identity")
            plan_key = f"ZU:{faculty_code}:{major_code}:P{plan_number}"
            programs.append(ProgramFact(
                plan_id=plan_id, plan_key=plan_key, plan_number=plan_number,
                total_credits=float(row.get("total_credit_hours") or 0),
                faculty_code=faculty_code, faculty_name_ar=str(faculty.get("name_ar") or faculty_code),
                major_code=major_code, major_name_ar=str(major.get("name_ar") or major_code),
            ))
            plan_ids.add(plan_id)
            if row.get("updated_at"):
                version_values.append(str(row["updated_at"]))

        courses: list[CourseFact] = []
        for row in course_rows:
            plan_id = str(row.get("study_plan_id") or "")
            if plan_id not in plan_ids:
                continue
            course = row.get("courses")
            group = row.get("requirement_groups")
            if not isinstance(course, Mapping) or not isinstance(group, Mapping):
                raise InstitutionalAnalyticsRepositoryError("Plan membership is missing course or requirement group")
            verified_groups: list[tuple[str, ...]] = []
            unresolved_codes: set[str] = set()
            for dependency_group in _list(row.get("course_dependency_groups")):
                if dependency_group.get("dependency_type") != "prerequisite":
                    continue
                options: list[str] = []
                group_verified = dependency_group.get("verification_status") == "verified"
                for option in _list(dependency_group.get("course_dependency_options")):
                    nested_course = option.get("courses")
                    code = str(nested_course.get("course_code") or "") if isinstance(nested_course, Mapping) else ""
                    if not code:
                        continue
                    if option.get("verification_status") not in {"verified", "referenced_only"}:
                        group_verified = False
                    options.append(code)
                if group_verified and options:
                    verified_groups.append(tuple(sorted(set(options))))
                else:
                    unresolved_codes.update(options)
            courses.append(CourseFact(
                membership_id=str(row.get("id") or ""), plan_id=plan_id,
                course_code=str(course.get("course_code") or ""),
                name_ar=_optional_text(course.get("name_ar")), name_en=_optional_text(course.get("name_en")),
                credits=float(row.get("credit_hours") or 0), display_order=int(row.get("display_order") or 0),
                requirement_group=str(group.get("group_code") or group.get("scope") or "UNKNOWN"),
                requirement_type=str(group.get("requirement_type") or "unknown"),
                prerequisite_status=str(row.get("prerequisite_logic_status") or row.get("verification_status") or "unresolved"),
                dependency_groups=tuple(verified_groups), unresolved_dependency_codes=tuple(sorted(unresolved_codes)),
            ))
            if row.get("updated_at"):
                version_values.append(str(row["updated_at"]))

        attempts_by_profile: dict[str, list[tuple[str, str]]] = defaultdict(list)
        state_versions: list[str] = []
        for row in attempt_rows:
            course = row.get("courses")
            if not isinstance(course, Mapping) or not course.get("course_code"):
                continue
            attempts_by_profile[str(row.get("profile_id"))].append(
                (str(course["course_code"]), str(row.get("outcome") or "")))
            if row.get("updated_at"):
                state_versions.append(str(row["updated_at"]))

        latest_intents: dict[tuple[str, str], tuple[int, tuple[str, ...]]] = {}
        for row in intent_rows:
            period = row.get("mock_registration_target_periods")
            if isinstance(period, Mapping) and str(period.get("period_key")) != term_key:
                continue
            key = (str(row.get("owner_user_id")), str(row.get("study_plan_id")))
            revision = int(row.get("revision") or 0)
            if key in latest_intents and latest_intents[key][0] >= revision:
                continue
            codes = tuple(sorted({str(item.get("course_code")) for item in _list(row.get("mock_registration_intent_courses"))
                                  if item.get("course_code")}))
            latest_intents[key] = (revision, codes)
            if row.get("created_at"):
                state_versions.append(str(row["created_at"]))

        students: list[StudentFact] = []
        for row in profile_rows:
            plan_id = str(row.get("study_plan_id") or "")
            if plan_id not in plan_ids:
                continue
            owner_id = str(row.get("owner_user_id") or "")
            profile_id = str(row.get("id") or "")
            students.append(StudentFact(
                owner_id=owner_id, profile_id=profile_id, plan_id=plan_id,
                earned_credits=_optional_float(row.get("reported_earned_credit_hours")),
                attempts=tuple(attempts_by_profile.get(profile_id, ())),
                planned_courses=latest_intents.get((owner_id, plan_id), (0, ()))[1],
            ))
            if row.get("updated_at"):
                state_versions.append(str(row["updated_at"]))

        return AnalyticsSnapshot(
            university_id=university_id, term_key=term_key,
            programs=tuple(sorted(programs, key=lambda item: item.plan_key)),
            courses=tuple(courses), students=tuple(students), sections=sections,
            catalog_version=max(version_values, default="UNAVAILABLE"),
            student_state_version=max(state_versions, default="UNAVAILABLE"),
            offering_version=offering_version, offering_complete=offering_complete,
            assigned_student_ids=assigned_student_ids,
        )

    async def _get(self, resource: str, params: Mapping[str, str]) -> list[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        page_size = 1000
        offset = 0
        while True:
            try:
                response = await self._client.get(
                    f"{self._rest_url}/{resource}", params=params,
                    headers={"apikey": self._server_key, "Authorization": f"Bearer {self._server_key}",
                             "Accept": "application/json", "Range-Unit": "items",
                             "Range": f"{offset}-{offset + page_size - 1}"}, timeout=15,
                )
            except (httpx.TimeoutException, httpx.RequestError) as error:
                raise InstitutionalAnalyticsRepositoryError(f"Unable to load {resource}") from error
            if not 200 <= response.status_code < 300:
                raise InstitutionalAnalyticsRepositoryError(
                    f"Unable to load {resource}: persistence status {response.status_code}")
            try:
                payload = response.json()
            except ValueError as error:
                raise InstitutionalAnalyticsRepositoryError(f"Invalid persistence response for {resource}") from error
            if not isinstance(payload, list) or any(not isinstance(row, Mapping) for row in payload):
                raise InstitutionalAnalyticsRepositoryError(f"Invalid persistence rows for {resource}")
            rows.extend(payload)
            if len(payload) < page_size:
                return rows
            offset += page_size


def _list(value: Any) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _optional_text(value: Any) -> str | None:
    return str(value) if value is not None and str(value).strip() else None


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None
