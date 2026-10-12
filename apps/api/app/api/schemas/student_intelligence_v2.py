"""Public schemas omit diagnostic answer keys and internal scoring weights."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SkillDimensionV2Response(BaseModel):
    skill_id: str
    score: int | None = Field(default=None, ge=0, le=100)
    confidence: str
    evidence_quality: str
    university_evidence_count: int
    diagnostic_evidence_count: int
    contributing_courses: list[str]
    contributing_question_domains: list[str]
    source_types: list[str]
    reason_codes: list[str]


class StudentIntelligenceProfileV2Response(BaseModel):
    student_id: str
    institution_id: str
    study_plan_id: str
    intelligence_model_version: str
    taxonomy_version: str
    fusion_policy_version: str
    generated_at: datetime
    source_snapshot_version: str
    cumulative_gpa: Decimal | None
    gpa_scale: Decimal | None
    earned_credits: Decimal
    verified_grade_count: int
    completed_course_count: int
    failed_course_count: int
    repeated_course_count: int
    current_course_count: int
    academic_progress_band: str
    performance_trend: str
    evidence_quality: str
    cold_start_status: str
    diagnostic_recommended: bool
    diagnostic_completed: bool
    latest_assessment_version: str | None
    latest_completed_at: datetime | None
    skills: list[SkillDimensionV2Response]
    strengths: list[str]
    development_areas: list[str]
    preferences: dict[str, Any]
    limitations: list[str]


class DiagnosticOptionResponse(BaseModel):
    option_id: str
    text_ar: str
    text_en: str


class DiagnosticQuestionResponse(BaseModel):
    question_id: str
    assessment_version: str
    domain: str
    prompt_ar: str
    prompt_en: str
    options: list[DiagnosticOptionResponse]


class DiagnosticSessionResponse(BaseModel):
    session_id: str
    status: str
    assessment_version: str
    answered_count: int
    maximum_questions: int
    question: DiagnosticQuestionResponse | None
    results: list[dict[str, Any]] | None = None
    intelligence_profile: StudentIntelligenceProfileV2Response | None = None


class DiagnosticStatusResponse(BaseModel):
    onboarding_status: str
    diagnostic_completed: bool
    active_session_id: str | None
    latest_assessment_version: str | None
    latest_completed_at: datetime | None


class DiagnosticAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str = Field(min_length=3, max_length=32)
    selected_option: str = Field(pattern="^[A-D]$")
