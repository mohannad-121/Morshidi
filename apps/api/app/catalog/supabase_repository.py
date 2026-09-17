"""Supabase Data API adapter that maps catalog rows to pure rules models."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

import httpx

from app.catalog.errors import (
    CatalogIntegrityError,
    CatalogTransportError,
    StudyPlanNotFound,
    TargetCourseNotFound,
    TargetCourseNotInStudyPlan,
)
from app.rules.models import (
    CanTakeCatalog,
    CourseCatalogStatus,
    CourseIdentity,
    DependencyGroup,
    DependencyType,
    PlanCourseRule,
    PrerequisiteLogicStatus,
)


class SupabaseAcademicCatalogRepository:
    """Read-only server-side adapter for the accepted academic catalog.

    ``server_key`` is used only as the Data API ``apikey`` credential.  It is
    deliberately never included in exception messages or stored in models.
    """

    def __init__(
        self,
        supabase_url: str,
        server_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not supabase_url.strip():
            raise ValueError("supabase_url must not be empty")
        if not server_key.strip():
            raise ValueError("server_key must not be empty")
        self._rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._server_key = server_key
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def close(self) -> None:
        """Close only a client created by this repository."""

        if self._owns_client:
            await self._client.aclose()

    async def load_target_rules(
        self,
        study_plan_id: UUID | str,
        target_course_code: str,
    ) -> CanTakeCatalog:
        """Resolve one plan target and map persisted dependency rows exactly."""

        plan_id = str(study_plan_id)
        plan = await self._load_study_plan(plan_id)
        university_id = self._university_id(plan)

        course_rows = await self._get_rows(
            "courses",
            {
                "select": "id,course_code,name_ar,catalog_status,university_id",
                "university_id": f"eq.{university_id}",
                "course_code": f"eq.{target_course_code}",
            },
        )
        if not course_rows:
            raise TargetCourseNotFound(
                "Target course code was not found in the study plan university"
            )
        if len(course_rows) != 1:
            raise CatalogIntegrityError("Multiple catalog courses matched one university code")
        target_course = course_rows[0]
        target_course_id = _required_text(target_course, "id", "course")
        self._course_identity(target_course)

        plan_course_rows = await self._get_rows(
            "study_plan_courses",
            {
                "select": "id,prerequisite_logic_status,raw_prerequisite_text",
                "study_plan_id": f"eq.{plan_id}",
                "course_id": f"eq.{target_course_id}",
            },
        )
        if not plan_course_rows:
            raise TargetCourseNotInStudyPlan(
                "Target course is not a member of the requested study plan"
            )
        if len(plan_course_rows) != 1:
            raise CatalogIntegrityError("Multiple study-plan memberships matched one target")
        plan_course = plan_course_rows[0]
        plan_course_id = _required_text(plan_course, "id", "study_plan_course")
        status = _enum_value(
            PrerequisiteLogicStatus,
            _required_text(plan_course, "prerequisite_logic_status", "study_plan_course"),
            "prerequisite_logic_status",
        )

        groups = await self._load_groups(plan_course_id)
        if status is PrerequisiteLogicStatus.NOT_APPLICABLE:
            if groups:
                raise CatalogIntegrityError("not_applicable target has dependency groups")
            dependency_groups: tuple[DependencyGroup, ...] = ()
            course_identities = (self._course_identity(target_course),)
        elif status in (
            PrerequisiteLogicStatus.UNRESOLVED,
            PrerequisiteLogicStatus.SOURCE_CONFLICT,
        ):
            if groups:
                raise CatalogIntegrityError("non-executable target has dependency groups")
            dependency_groups = ()
            course_identities = (self._course_identity(target_course),)
        else:
            if not groups:
                raise CatalogIntegrityError("verified target has no dependency group representation")
            dependency_groups, option_identities = await self._load_verified_dependencies(
                groups,
                university_id,
            )
            course_identities = _sorted_unique_course_identities(
                (self._course_identity(target_course), *option_identities)
            )

        raw_text = plan_course.get("raw_prerequisite_text")
        if raw_text is not None and not isinstance(raw_text, str):
            raise CatalogIntegrityError("raw_prerequisite_text is not text")
        target_name_ar = target_course.get("name_ar")
        if target_name_ar is not None and not isinstance(target_name_ar, str):
            raise CatalogIntegrityError("course name_ar is not text")
        target_code = _required_text(target_course, "course_code", "course")
        if target_code != target_course_code:
            raise CatalogIntegrityError("course response did not match requested target code")

        return CanTakeCatalog(
            study_plan_id=plan_id,
            plan_courses=(
                PlanCourseRule(
                    course_code=target_code,
                    prerequisite_logic_status=status,
                    dependency_groups=dependency_groups,
                    raw_prerequisite_text=raw_text,
                    target_name_ar=target_name_ar,
                ),
            ),
            courses=course_identities,
        )

    async def _load_study_plan(self, plan_id: str) -> Mapping[str, Any]:
        rows = await self._get_rows(
            "study_plans",
            {
                "select": "id,majors(faculties(university_id))",
                "id": f"eq.{plan_id}",
            },
        )
        if not rows:
            raise StudyPlanNotFound("Study plan was not found")
        if len(rows) != 1:
            raise CatalogIntegrityError("Multiple study plans matched one identifier")
        return rows[0]

    async def _load_groups(self, plan_course_id: str) -> tuple[Mapping[str, Any], ...]:
        rows = await self._get_rows(
            "course_dependency_groups",
            {
                "select": "id,dependency_type,group_number",
                "study_plan_course_id": f"eq.{plan_course_id}",
            },
        )
        return tuple(rows)

    async def _load_verified_dependencies(
        self,
        groups: Sequence[Mapping[str, Any]],
        university_id: str,
    ) -> tuple[tuple[DependencyGroup, ...], tuple[CourseIdentity, ...]]:
        normalized_groups: list[tuple[str, DependencyType, int]] = []
        group_numbers: set[int] = set()
        for row in groups:
            group_id = _required_text(row, "id", "dependency group")
            dependency_type = _enum_value(
                DependencyType,
                _required_text(row, "dependency_type", "dependency group"),
                "dependency_type",
            )
            number = _required_positive_int(row, "group_number", "dependency group")
            if number in group_numbers:
                raise CatalogIntegrityError("Duplicate dependency group_number in target")
            group_numbers.add(number)
            normalized_groups.append((group_id, dependency_type, number))

        group_ids = [group_id for group_id, _, _ in normalized_groups]
        option_rows = await self._get_rows(
            "course_dependency_options",
            {
                "select": "dependency_group_id,courses(course_code,catalog_status,university_id)",
                "dependency_group_id": f"in.({','.join(group_ids)})",
            },
        )
        options_by_group: dict[str, list[CourseIdentity]] = {group_id: [] for group_id in group_ids}
        for row in option_rows:
            group_id = _required_text(row, "dependency_group_id", "dependency option")
            if group_id not in options_by_group:
                raise CatalogIntegrityError("Dependency option belongs to an unexpected group")
            nested_course = row.get("courses")
            if not isinstance(nested_course, Mapping):
                raise CatalogIntegrityError("Dependency option is missing its referenced course")
            option_university_id = _required_text(nested_course, "university_id", "dependency course")
            if option_university_id != university_id:
                raise CatalogIntegrityError("Dependency course belongs to another university")
            options_by_group[group_id].append(self._course_identity(nested_course))

        result_groups: list[DependencyGroup] = []
        all_identities: list[CourseIdentity] = []
        for group_id, dependency_type, group_number in sorted(
            normalized_groups,
            key=lambda item: item[2],
        ):
            identities = options_by_group[group_id]
            if not identities:
                raise CatalogIntegrityError("Dependency group has no options")
            codes = [identity.course_code for identity in identities]
            if len(codes) != len(set(codes)):
                raise CatalogIntegrityError("Dependency group has duplicate option courses")
            ordered = tuple(sorted(identities, key=lambda identity: identity.course_code))
            result_groups.append(
                DependencyGroup(
                    group_number=group_number,
                    dependency_type=dependency_type,
                    option_course_codes=tuple(identity.course_code for identity in ordered),
                )
            )
            all_identities.extend(ordered)
        return tuple(result_groups), tuple(all_identities)

    async def _get_rows(
        self,
        resource: str,
        params: Mapping[str, str],
    ) -> list[Mapping[str, Any]]:
        try:
            response = await self._client.get(
                f"{self._rest_url}/{resource}",
                params=params,
                headers={
                    "apikey": self._server_key,
                    "Authorization": f"Bearer {self._server_key}",
                    "Accept": "application/json",
                },
            )
        except (httpx.TimeoutException, httpx.RequestError) as error:
            raise CatalogTransportError("GET", resource) from error
        if not 200 <= response.status_code < 300:
            raise CatalogTransportError("GET", resource, status_code=response.status_code)
        try:
            body = response.json()
        except ValueError as error:
            raise CatalogTransportError("decode response", resource) from error
        if not isinstance(body, list) or not all(isinstance(row, Mapping) for row in body):
            raise CatalogIntegrityError(f"{resource} response is not a row array")
        return list(body)

    @staticmethod
    def _university_id(plan: Mapping[str, Any]) -> str:
        majors = plan.get("majors")
        if not isinstance(majors, Mapping):
            raise CatalogIntegrityError("Study plan is missing its major relationship")
        faculties = majors.get("faculties")
        if not isinstance(faculties, Mapping):
            raise CatalogIntegrityError("Study plan is missing its faculty relationship")
        return _required_text(faculties, "university_id", "faculty")

    @staticmethod
    def _course_identity(row: Mapping[str, Any]) -> CourseIdentity:
        return CourseIdentity(
            course_code=_required_text(row, "course_code", "course"),
            catalog_status=_enum_value(
                CourseCatalogStatus,
                _required_text(row, "catalog_status", "course"),
                "catalog_status",
            ),
        )


def _required_text(row: Mapping[str, Any], field: str, resource: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise CatalogIntegrityError(f"{resource} is missing required {field}")
    return value


def _required_positive_int(row: Mapping[str, Any], field: str, resource: str) -> int:
    value = row.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CatalogIntegrityError(f"{resource} has invalid {field}")
    return value


def _enum_value(enum_type: type[Any], value: str, field: str) -> Any:
    try:
        return enum_type(value)
    except ValueError as error:
        raise CatalogIntegrityError(f"Unsupported {field}: {value}") from error


def _sorted_unique_course_identities(
    identities: Sequence[CourseIdentity],
) -> tuple[CourseIdentity, ...]:
    by_code: dict[str, CourseIdentity] = {}
    for identity in identities:
        previous = by_code.setdefault(identity.course_code, identity)
        if previous != identity:
            raise CatalogIntegrityError("Course code has conflicting catalog identities")
    return tuple(sorted(by_code.values(), key=lambda identity: identity.course_code))
