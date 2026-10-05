"""Strict academic catalog mapping for the synthetic Sandbox University."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping, Sequence

from app.advisor.models import ResolvedCourseReference
from app.catalog.display import CourseDisplayIdentity
from app.catalog.roadmap_metadata import RoadmapPlanMetadata
from app.p16_sandbox.tenant import SANDBOX_INSTITUTION_ID, SANDBOX_PLAN_ID
from app.p16_sandbox.transport import SandboxUniversityTransport, StaticFixtureTransport
from app.rules.models import (
    CanTakeCatalog,
    CourseCatalogStatus,
    CourseIdentity,
    DependencyGroup,
    DependencyType,
    PlanCourseRule,
    PrerequisiteLogicStatus,
)


SANDBOX_RULE_AUTHORITY = "SYNTHETIC_SANDBOX_ACADEMIC_POLICY"
SANDBOX_RULE_VERSION = "2026.10.05.v1"
SANDBOX_PREREQUISITE_SEMANTICS = "ALL_OF"


class SandboxAcademicPolicyError(RuntimeError):
    """The synthetic fixture cannot be mapped without making an inference."""


class SandboxAcademicCatalogRepository:
    """Map the explicit synthetic fixture policy to the deterministic engine.

    Every prerequisite is represented as its own one-option group. The engine
    ANDs groups and ORs options inside a group, so this is the exact ALL_OF
    representation and does not special-case an individual course.
    """

    def __init__(self, transport: SandboxUniversityTransport | None = None) -> None:
        self._transport = transport or StaticFixtureTransport()

    async def _snapshot(self) -> tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]:
        manifest = await self._transport.load_manifest()
        courses = await self._transport.load_courses()
        if manifest.get("institution_id") != SANDBOX_INSTITUTION_ID:
            raise SandboxAcademicPolicyError("Sandbox manifest institution is invalid")
        if str(manifest.get("plan_id")) != SANDBOX_PLAN_ID or manifest.get("synthetic") is not True:
            raise SandboxAcademicPolicyError("Sandbox manifest plan identity is invalid")
        policy = manifest.get("academic_policy")
        if not isinstance(policy, Mapping):
            raise SandboxAcademicPolicyError("Sandbox academic policy is missing")
        expected = {
            "authority": SANDBOX_RULE_AUTHORITY,
            "rule_version": SANDBOX_RULE_VERSION,
            "prerequisite_list_semantics": SANDBOX_PREREQUISITE_SEMANTICS,
            "minimum_grade_condition": None,
            "review_required_semantics": "NON_EXECUTABLE",
        }
        if any(policy.get(key) != value for key, value in expected.items()):
            raise SandboxAcademicPolicyError("Sandbox academic policy contract is invalid")
        return manifest, courses

    async def load_plan_eligibility_catalog(self, study_plan_id: str) -> CanTakeCatalog:
        if str(study_plan_id) != SANDBOX_PLAN_ID:
            raise SandboxAcademicPolicyError("Sandbox study plan is invalid")
        _, rows = await self._snapshot()
        identities: list[CourseIdentity] = []
        rules: list[PlanCourseRule] = []
        seen: set[str] = set()
        for row in rows:
            code = _required_text(row, "code")
            name = _required_text(row, "name")
            if code in seen:
                raise SandboxAcademicPolicyError("Sandbox course codes are not unique")
            seen.add(code)
            prerequisites = _prerequisites(row)
            review_required = row.get("review_required")
            if not isinstance(review_required, bool):
                raise SandboxAcademicPolicyError("Sandbox review flag is invalid")
            identities.append(CourseIdentity(code, CourseCatalogStatus.KNOWN))
            if review_required:
                status = PrerequisiteLogicStatus.UNRESOLVED
                groups: tuple[DependencyGroup, ...] = ()
            elif prerequisites:
                status = PrerequisiteLogicStatus.VERIFIED
                groups = tuple(
                    DependencyGroup(index, DependencyType.PREREQUISITE, (prerequisite,))
                    for index, prerequisite in enumerate(prerequisites, start=1)
                )
            else:
                status = PrerequisiteLogicStatus.NOT_APPLICABLE
                groups = ()
            rules.append(
                PlanCourseRule(
                    course_code=code,
                    prerequisite_logic_status=status,
                    dependency_groups=groups,
                    raw_prerequisite_text=",".join(prerequisites) or None,
                    target_name_ar=name,
                    credit_hours=_nonnegative_decimal(row, "credits"),
                )
            )
        unknown = sorted(
            prerequisite
            for rule in rules
            for group in rule.dependency_groups
            for prerequisite in group.option_course_codes
            if prerequisite not in seen
        )
        identities.extend(
            CourseIdentity(code, CourseCatalogStatus.REFERENCED_ONLY) for code in unknown
        )
        return CanTakeCatalog(
            SANDBOX_PLAN_ID,
            tuple(rules),
            tuple(sorted(identities, key=lambda item: item.course_code)),
        )

    async def load_target_rules(self, study_plan_id: str, target_course_code: str) -> CanTakeCatalog:
        catalog = await self.load_plan_eligibility_catalog(study_plan_id)
        rules = tuple(rule for rule in catalog.plan_courses if rule.course_code == target_course_code)
        return CanTakeCatalog(catalog.study_plan_id, rules, catalog.courses)

    async def load_advisor_course_catalog(
        self, study_plan_id: str,
    ) -> tuple[ResolvedCourseReference, ...]:
        if str(study_plan_id) != SANDBOX_PLAN_ID:
            raise SandboxAcademicPolicyError("Sandbox study plan is invalid")
        _, rows = await self._snapshot()
        return tuple(sorted(
            (ResolvedCourseReference(_required_text(row, "code"), _required_text(row, "name"))
             for row in rows),
            key=lambda item: item.course_code,
        ))

    async def load_university_course_identities(
        self, university_id: str,
    ) -> tuple[CourseDisplayIdentity, ...]:
        if university_id != SANDBOX_INSTITUTION_ID:
            raise SandboxAcademicPolicyError("Sandbox institution is invalid")
        _, rows = await self._snapshot()
        return tuple(
            CourseDisplayIdentity(_required_text(row, "code"), _required_text(row, "code"),
                                  _required_text(row, "name"), None)
            for row in rows
        )

    async def load_progress_catalog(self, study_plan_id: str):
        raise SandboxAcademicPolicyError(
            "Synthetic progress requirements are not explicit in the sandbox contract"
        )

    async def load_roadmap_plan_metadata(self, study_plan_id: str) -> RoadmapPlanMetadata:
        if str(study_plan_id) != SANDBOX_PLAN_ID:
            raise SandboxAcademicPolicyError("Sandbox study plan is invalid")
        return RoadmapPlanMetadata(
            SANDBOX_PLAN_ID, SANDBOX_PLAN_ID, None, "2026-10-05T00:00:00Z",
            SANDBOX_RULE_AUTHORITY, None, None, None, "synthetic",
        )


def _required_text(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SandboxAcademicPolicyError(f"Sandbox course {key} is invalid")
    return value.strip()


def _prerequisites(row: Mapping[str, Any]) -> tuple[str, ...]:
    value = row.get("prerequisites")
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise SandboxAcademicPolicyError("Sandbox prerequisites are invalid")
    if len(value) != len(set(value)):
        raise SandboxAcademicPolicyError("Sandbox prerequisites contain duplicates")
    return tuple(value)


def _nonnegative_decimal(row: Mapping[str, Any], key: str) -> Decimal:
    value = row.get(key)
    if isinstance(value, bool):
        raise SandboxAcademicPolicyError(f"Sandbox course {key} is invalid")
    try:
        result = Decimal(str(value))
    except Exception as error:
        raise SandboxAcademicPolicyError(f"Sandbox course {key} is invalid") from error
    if not result.is_finite() or result < 0:
        raise SandboxAcademicPolicyError(f"Sandbox course {key} is invalid")
    return result
