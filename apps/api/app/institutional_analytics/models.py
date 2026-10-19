"""Typed production contracts for deterministic Institutional Intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


MetricStatus = Literal["AVAILABLE", "INSUFFICIENT_DATA", "SUPPRESSED", "UNAVAILABLE"]


class Metric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int | float | None
    status: MetricStatus = "AVAILABLE"
    unit: str
    inputs: dict[str, int | float | str | bool | None] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)


class ProjectionComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")
    currently_eligible: int
    planner_selected: int
    degree_path_upcoming: int
    excluded_completed_or_registered: int


class ProgramBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_key: str
    faculty_code: str
    major_code: str
    student_count: int
    demand_count: int


class CourseMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_code: str
    name_ar: str | None = None
    name_en: str | None = None
    programs: list[str]
    requirement_categories: list[str]
    prerequisite_status: Literal["VERIFIED", "REVIEW_REQUIRED", "NOT_APPLICABLE"]
    current_registered: Metric
    eligible_not_registered: Metric
    planned_need: Metric
    degree_path_need: Metric
    projected_demand: Metric
    projection_confidence: Literal["HIGH", "MEDIUM", "LOW", "INSUFFICIENT_DATA"]
    projection_components: ProjectionComponents
    offered_seats: Metric
    available_seats: Metric
    utilization_percent: Metric
    demand_capacity_gap: Metric
    capacity_state: Literal["UNDER_CAPACITY", "HEALTHY", "NEAR_CAPACITY", "OVER_DEMAND", "UNAVAILABLE"]
    bottleneck_score: int
    bottleneck_level: Literal["NONE", "WATCH", "HIGH", "CRITICAL"]
    bottleneck_reasons: list[str]
    affected_student_count: int
    downstream_course_count: int
    programs_affected: list[str]
    action_recommendation: str | None = None
    estimated_students_helped: int = 0
    demand_by_program: list[ProgramBreakdown]


class ProgressBand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    band: Literal["0_24", "25_49", "50_74", "75_89", "90_100"]
    student_count: int | None
    status: MetricStatus


class ProgramMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_id: str
    plan_key: str
    plan_number: str
    faculty_code: str
    faculty_name_ar: str
    major_code: str
    major_name_ar: str
    student_count: int
    data_status: MetricStatus
    average_progress_percent: float | None
    average_earned_credits: float | None
    median_earned_credits: float | None
    current_registered_credits: float
    blocked_student_count: int | None
    review_required_count: int | None
    progress_distribution: list[ProgressBand]
    high_demand_courses: list[str]
    bottleneck_courses: list[str]


class ReviewQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    course_code: str
    unresolved_prerequisite_codes: list[str]
    affected_plans: list[str]
    affected_student_count: int | None
    downstream_course_count: int
    system_behavior: Literal["FAIL_CLOSED"] = "FAIL_CLOSED"


class AdvisorCaseload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: Literal["INSTITUTION", "ASSIGNED_STUDENTS"]
    assigned_student_count: int | None = None
    prerequisite_review: int
    blocked_degree_paths: int
    near_graduation: int
    registration_conflicts: Metric
    approaching_credit_limit: Metric
    without_viable_semester_plan: int
    impacted_by_high_pressure_courses: int
    reason_codes: list[str]


class Overview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_active_students: Metric
    current_registrations: Metric
    average_registered_credit_load: Metric
    eligible_course_opportunities: Metric
    blocked_by_prerequisite: Metric
    review_required: Metric
    high_demand_courses: Metric
    capacity_pressure_courses: Metric
    academic_bottlenecks: Metric
    approaching_graduation: Metric
    blocked_degree_paths: Metric
    students_by_faculty: dict[str, int]
    students_by_major: dict[str, int]


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["INSTITUTIONAL_INTELLIGENCE_DASHBOARD"] = "INSTITUTIONAL_INTELLIGENCE_DASHBOARD"
    contract_version: Literal["2.0"] = "2.0"
    university_id: str
    term_key: str
    role_scope: Literal["INSTITUTION_ADMIN", "ADVISOR_ASSIGNED"]
    filters: dict[str, str | None]
    minimum_cohort_size: int
    overview: Overview
    programs: list[ProgramMetric]
    courses: list[CourseMetric]
    review_queue: list[ReviewQueueItem]
    advisor_caseload: AdvisorCaseload
    methodology: dict[str, str]
    source_versions: dict[str, str]
    generated_at: datetime


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    university_id: str
    term_key: str
    course_code: str = Field(min_length=1, max_length=50)
    kind: Literal["ADD_SECTION", "REMOVE_OFFERING", "CHANGE_SECTION_CAPACITY"]
    seats: int | None = Field(default=None, ge=0, le=500)
    section_id: str | None = Field(default=None, max_length=100)


class SimulationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    simulation_only: Literal[True] = True
    course_code: str
    kind: str
    capacity_before: int | None
    capacity_after: int | None
    demand_gap_before: int | None
    demand_gap_after: int | None
    estimated_students_helped: int
    bottleneck_score_before: int
    bottleneck_score_after: int
    affected_programs: list[str]
    affected_eligible_students: int
    affected_degree_paths: int
    downstream_courses_impacted: int
    assumptions: list[str]


@dataclass(frozen=True)
class ProgramFact:
    plan_id: str
    plan_key: str
    plan_number: str
    total_credits: float
    faculty_code: str
    faculty_name_ar: str
    major_code: str
    major_name_ar: str


@dataclass(frozen=True)
class CourseFact:
    membership_id: str
    plan_id: str
    course_code: str
    name_ar: str | None
    name_en: str | None
    credits: float
    display_order: int
    requirement_group: str
    requirement_type: str
    prerequisite_status: str
    dependency_groups: tuple[tuple[str, ...], ...] = ()
    unresolved_dependency_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class StudentFact:
    owner_id: str
    profile_id: str
    plan_id: str
    earned_credits: float | None
    attempts: tuple[tuple[str, str], ...]
    planned_courses: tuple[str, ...] = ()


@dataclass(frozen=True)
class SectionFact:
    section_id: str
    course_code: str
    capacity: int | None
    enrolled: int | None
    available: int | None
    status: str | None


@dataclass(frozen=True)
class AnalyticsSnapshot:
    university_id: str
    term_key: str
    programs: tuple[ProgramFact, ...]
    courses: tuple[CourseFact, ...]
    students: tuple[StudentFact, ...]
    sections: tuple[SectionFact, ...] | None
    catalog_version: str
    student_state_version: str
    offering_version: str | None
    offering_complete: bool = False
    assigned_student_ids: frozenset[str] | None = field(default=None)
