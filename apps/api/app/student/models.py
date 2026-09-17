"""Thin persistence aggregate; eligibility facts remain Phase 5 models."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.rules.models import AttemptOutcome, StudentCourseAttempt


@dataclass(frozen=True)
class StudentAcademicState:
    profile_id: str
    owner_user_id: str
    study_plan_id: str
    reported_cumulative_gpa: Decimal | None
    reported_gpa_scale: Decimal | None
    reported_earned_credit_hours: Decimal | None
    attempts: tuple[StudentCourseAttempt, ...]
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class StudentCourseAttemptRecord:
    attempt_id: str
    profile_id: str
    course_code: str
    outcome: AttemptOutcome
    attempt_sequence: int | None
    term_label: str | None
    attempted_on: date | None
    reported_grade_text: str | None
    record_source: str
    created_at: datetime
    updated_at: datetime
