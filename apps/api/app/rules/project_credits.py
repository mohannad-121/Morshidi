"""Compatibility helpers for the authoritative graduation-policy registry."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from app.rules.models import AttemptOutcome, CanTakeCatalog, StudentCourseAttempt
from app.graduation_policy.catalog import (
    AI_PLAN_12_ID,
    AI_PROJECT_CODES,
    DEFAULT_GRADUATION_POLICY_REGISTRY,
)
from app.graduation_policy.models import PolicyRuleKind

if TYPE_CHECKING:
    from app.progress.models import AcademicProgress

RULE_ID = "GRADUATION_PROJECT_MIN_EARNED_CREDITS"
RULE_VERSION = "P15_5_PROJECT_CREDITS_V1"
RULE_PROVENANCE = "OWNER_APPROVED_PLAN12_PROJECT_REQUIREMENT"
PLAN12_ID = AI_PLAN_12_ID
PROJECT_CODES = frozenset(AI_PROJECT_CODES)
MIN_EARNED_CREDITS = Decimal("90")


def is_plan12_project(study_plan_id: str, course_code: str) -> bool:
    return any(
        rule.kind is PolicyRuleKind.MIN_EARNED_CREDITS_FOR_COURSE
        for rule in DEFAULT_GRADUATION_POLICY_REGISTRY.rules_for_course(
            study_plan_id, course_code
        )
    )


def passed_plan_credits(progress: AcademicProgress) -> Decimal:
    """Successfully completed listed-plan credits, not planned or attempted hours."""
    return sum((course.credit_hours for course in progress.courses
                if course.state.value == "COMPLETED"), Decimal(0))


def credits_from_complete_rules(catalog: CanTakeCatalog,
                                attempts: tuple[StudentCourseAttempt, ...]) -> Decimal | None:
    """Only a complete plan snapshot can establish a modeled earned-credit total."""
    if not catalog.complete_plan_credits:
        return None
    credits = {rule.course_code: rule.credit_hours for rule in catalog.plan_courses}
    if any(value is None or not value.is_finite() or value < 0 for value in credits.values()):
        return None
    passed = {item.course_code for item in attempts if item.outcome is AttemptOutcome.PASSED}
    return sum((credits[code] for code in passed if code in credits), Decimal(0))
