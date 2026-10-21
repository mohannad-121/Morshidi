"""Deterministic free-elective option gate.

This module never discovers or guesses courses. Callers may evaluate only a real
catalog course backed by an authoritative university free-elective policy row.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FreeElectiveCourseDecision(str, Enum):
    FREE_ELECTIVE_POLICY_REQUIRED = "FREE_ELECTIVE_POLICY_REQUIRED"
    COURSE_NOT_APPROVED_AS_FREE_ELECTIVE = "COURSE_NOT_APPROVED_AS_FREE_ELECTIVE"
    COURSE_ALREADY_COUNTED = "COURSE_ALREADY_COUNTED"
    COURSE_ALREADY_COMPLETED = "COURSE_ALREADY_COMPLETED"
    COURSE_ALREADY_REGISTERED = "COURSE_ALREADY_REGISTERED"
    COURSE_NOT_OFFERED = "COURSE_NOT_OFFERED"
    PREREQUISITE_BLOCKED = "PREREQUISITE_BLOCKED"
    COURSE_ELIGIBLE_AS_FREE_ELECTIVE = "COURSE_ELIGIBLE_AS_FREE_ELECTIVE"


@dataclass(frozen=True)
class FreeElectiveCourseContext:
    policy_available: bool
    approved_by_policy: bool
    offered_in_term: bool
    prerequisites_satisfied: bool
    already_completed: bool = False
    already_registered: bool = False
    already_counted_toward_degree: bool = False


def evaluate_free_elective_course(context: FreeElectiveCourseContext) -> FreeElectiveCourseDecision:
    """Apply the fail-closed option gate in stable academic-policy order."""
    if not context.policy_available:
        return FreeElectiveCourseDecision.FREE_ELECTIVE_POLICY_REQUIRED
    if not context.approved_by_policy:
        return FreeElectiveCourseDecision.COURSE_NOT_APPROVED_AS_FREE_ELECTIVE
    if context.already_counted_toward_degree:
        return FreeElectiveCourseDecision.COURSE_ALREADY_COUNTED
    if context.already_completed:
        return FreeElectiveCourseDecision.COURSE_ALREADY_COMPLETED
    if context.already_registered:
        return FreeElectiveCourseDecision.COURSE_ALREADY_REGISTERED
    if not context.offered_in_term:
        return FreeElectiveCourseDecision.COURSE_NOT_OFFERED
    if not context.prerequisites_satisfied:
        return FreeElectiveCourseDecision.PREREQUISITE_BLOCKED
    return FreeElectiveCourseDecision.COURSE_ELIGIBLE_AS_FREE_ELECTIVE
