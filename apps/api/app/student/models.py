"""Thin persistence aggregate; eligibility facts remain Phase 5 models."""

from dataclasses import dataclass
from decimal import Decimal

from app.rules.models import StudentCourseAttempt


@dataclass(frozen=True)
class StudentAcademicState:
    profile_id: str
    owner_user_id: str
    study_plan_id: str
    reported_cumulative_gpa: Decimal | None
    reported_gpa_scale: Decimal | None
    reported_earned_credit_hours: Decimal | None
    attempts: tuple[StudentCourseAttempt, ...]
