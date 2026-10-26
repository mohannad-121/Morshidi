"""Immutable graduation-policy model; LLMs never create or decide these rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class PolicyLifecycleStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    RETIRED = "retired"


class PolicyScopeLevel(str, Enum):
    UNIVERSITY = "university"
    DEGREE_LEVEL = "degree_level"
    FACULTY = "faculty"
    PROGRAM = "program"
    STUDY_PLAN = "study_plan"


class PolicyRuleKind(str, Enum):
    MIN_EARNED_CREDITS_FOR_COURSE = "min_earned_credits_for_course"
    SEQUENCED_COURSES = "sequenced_courses"
    MANDATORY_ZERO_CREDIT_COURSE = "mandatory_zero_credit_course"
    MINIMUM_GPA = "minimum_gpa"
    REMEDIAL_COURSE = "remedial_course"
    RESIDENCY_REQUIREMENT = "residency_requirement"
    INTERNSHIP_REQUIREMENT = "internship_requirement"


@dataclass(frozen=True)
class PolicyScope:
    level: PolicyScopeLevel
    university_id: str
    degree_level: str | None = None
    faculty_id: str | None = None
    program_id: str | None = None
    study_plan_id: str | None = None

    def __post_init__(self) -> None:
        required = {
            PolicyScopeLevel.DEGREE_LEVEL: self.degree_level,
            PolicyScopeLevel.FACULTY: self.faculty_id,
            PolicyScopeLevel.PROGRAM: self.program_id,
            PolicyScopeLevel.STUDY_PLAN: self.study_plan_id,
        }.get(self.level, self.university_id)
        if not self.university_id or not required:
            raise ValueError(f"Incomplete {self.level.value} policy scope")


@dataclass(frozen=True)
class GraduationPolicyRule:
    rule_id: str
    version: str
    kind: PolicyRuleKind
    provenance: str
    target_course_codes: tuple[str, ...] = ()
    minimum_credits: Decimal | None = None
    sequence_course_codes: tuple[str, ...] = ()
    source_reference: str | None = None

    def __post_init__(self) -> None:
        if not self.rule_id or not self.version or not self.provenance:
            raise ValueError("Policy rules require identity, version, and provenance")
        if self.kind is PolicyRuleKind.MIN_EARNED_CREDITS_FOR_COURSE:
            if not self.target_course_codes or self.minimum_credits is None:
                raise ValueError("Earned-credit rules require targets and a threshold")
            if not self.minimum_credits.is_finite() or self.minimum_credits < 0:
                raise ValueError("Earned-credit threshold must be finite and non-negative")


@dataclass(frozen=True)
class GraduationPolicyVersion:
    policy_id: str
    version: str
    scope: PolicyScope
    status: PolicyLifecycleStatus
    effective_from: date
    effective_to: date | None
    rules: tuple[GraduationPolicyRule, ...]

    def is_effective(self, on_date: date) -> bool:
        return (
            self.status is PolicyLifecycleStatus.APPROVED
            and self.effective_from <= on_date
            and (self.effective_to is None or on_date <= self.effective_to)
        )


class GraduationPolicyRegistry:
    """Resolve only approved, effective, explicitly matching policy scopes."""

    def __init__(self, policies: tuple[GraduationPolicyVersion, ...] = ()) -> None:
        self._policies = policies

    def rules_for_course(
        self,
        study_plan_id: str,
        course_code: str,
        *,
        on_date: date | None = None,
    ) -> tuple[GraduationPolicyRule, ...]:
        today = on_date or date.today()
        matches = (
            policy
            for policy in self._policies
            if policy.scope.level is PolicyScopeLevel.STUDY_PLAN
            and policy.scope.study_plan_id == study_plan_id
            and policy.is_effective(today)
        )
        return tuple(
            rule
            for policy in sorted(matches, key=lambda item: (item.effective_from, item.version))
            for rule in policy.rules
            if course_code in rule.target_course_codes
        )
