"""Normalized DTOs and database models for the generic SIS integration framework."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .capabilities import PilotMode, SISCapability, TenantStatus

MORSHIDI_SIS_CONTRACT_VERSION = "MORSHIDI_SIS_CONTRACT_V1"


# --- NORMALIZED SIS DTOs (Separates provider JSON shapes from Morshidi core) ---

class NormalizedStudent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: str = MORSHIDI_SIS_CONTRACT_VERSION
    university_student_id: str = Field(min_length=1)
    full_name: str | None = None
    email: str | None = None
    faculty_code: str | None = None
    major_code: str | None = None
    plan_key: str | None = None
    plan_number: str | None = None
    academic_standing: str | None = None
    cumulative_gpa: Decimal | None = None
    gpa_scale: Decimal | None = None
    earned_credit_hours: Decimal | None = None
    registered_credit_hours: Decimal | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class NormalizedCourse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: str = MORSHIDI_SIS_CONTRACT_VERSION
    course_code: str = Field(min_length=1)
    name_ar: str | None = None
    name_en: str | None = None
    credit_hours: Decimal = Field(default=Decimal("3"))
    faculty_code: str | None = None
    department_code: str | None = None
    prerequisite_codes: list[str] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class NormalizedGradeAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: str = MORSHIDI_SIS_CONTRACT_VERSION
    course_code: str = Field(min_length=1)
    term_code: str = Field(min_length=1)
    outcome: Literal["PASSED", "FAILED", "WITHDRAWN", "IN_PROGRESS"]
    numeric_grade: Decimal | None = None
    letter_grade: str | None = None
    credit_hours: Decimal | None = None
    is_official: bool = True
    attempt_sequence: int = 1
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class NormalizedEnrollment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: str = MORSHIDI_SIS_CONTRACT_VERSION
    course_code: str = Field(min_length=1)
    section_code: str = Field(min_length=1)
    term_code: str = Field(min_length=1)
    status: Literal["ENROLLED", "WAITLISTED", "DROPPED"] = "ENROLLED"
    credit_hours: Decimal = Field(default=Decimal("3"))
    enrolled_at: datetime | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class NormalizedStudyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: str = MORSHIDI_SIS_CONTRACT_VERSION
    plan_key: str = Field(min_length=1)
    plan_number: str | None = None
    faculty_code: str | None = None
    major_code: str | None = None
    total_credit_hours: Decimal
    required_courses: list[str] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class NormalizedOffering(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: str = MORSHIDI_SIS_CONTRACT_VERSION
    section_id: str = Field(min_length=1)
    course_code: str = Field(min_length=1)
    term_code: str = Field(min_length=1)
    section_number: str = "1"
    instructor_name: str | None = None
    capacity: int = 30
    enrolled: int = 0
    available: int = 30
    status: str = "OPEN"
    schedule_summary: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class NormalizedTerm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contract_version: str = MORSHIDI_SIS_CONTRACT_VERSION
    term_code: str = Field(min_length=1)
    term_name_ar: str
    term_name_en: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    is_registration_open: bool = False


class NormalizedAuthResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    authenticated: bool
    university_student_id: str
    token: str | None = None
    full_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["HEALTHY", "DEGRADED", "UNHEALTHY", "NOT_CONFIGURED"]
    connectivity: bool
    latency_ms: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class ChangeBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cursor: str | None = None
    has_more: bool = False
    students: list[NormalizedStudent] = Field(default_factory=list)
    grades: list[NormalizedGradeAttempt] = Field(default_factory=list)
    enrollments: list[NormalizedEnrollment] = Field(default_factory=list)


# --- PERSISTED TENANT & INTEGRATION MODELS ---

class UniversityTenant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    tenant_key: str
    name_ar: str
    name_en: str | None = None
    country: str
    timezone: str = "Asia/Amman"
    default_locale: str = "ar"
    status: TenantStatus = TenantStatus.ACTIVE
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UniversityIntegrationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID | None = None
    university_id: UUID
    provider_type: str
    base_url: str
    auth_method: str = "client_credentials"
    client_id: str | None = None
    secret_env_ref: str | None = None
    token_url: str | None = None
    api_version: str = "v1"
    supported_capabilities: list[SISCapability] = Field(default_factory=list)
    pilot_mode: PilotMode = PilotMode.READ_ONLY_PILOT
    feature_flags: dict[str, bool] = Field(default_factory=dict)
    timeouts_ms: dict[str, int] = Field(default_factory=lambda: {"connect": 5000, "read": 10000})
    rate_limit_rpm: int = 600
    webhook_secret_env_ref: str | None = None
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UniversityMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID | None = None
    university_id: UUID
    entity_type: Literal["FACULTY", "MAJOR", "PLAN", "COURSE", "TERM", "SECTION"]
    external_code: str
    canonical_id: str
    canonical_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SyncJob(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID | None = None
    university_id: UUID
    sync_mode: Literal["FULL_SYNC", "INCREMENTAL_SYNC", "EVENT_DRIVEN"]
    status: Literal["PENDING", "RUNNING", "SUCCEEDED", "PARTIAL", "FAILED"] = "PENDING"
    cursor_before: str | None = None
    cursor_after: str | None = None
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    records_skipped: int = 0
    records_failed: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_ms: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class ReconciliationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID | None = None
    university_id: UUID
    entity_type: Literal["STUDENT", "ENROLLMENT", "GRADE", "PLAN", "COURSE"]
    external_identifier: str
    status: Literal["IN_SYNC", "MISSING_LOCALLY", "STALE_LOCALLY", "VALUE_MISMATCH", "IDENTITY_MISMATCH", "MAPPING_MISSING"]
    details: dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None


class PilotReadinessScorecard(BaseModel):
    model_config = ConfigDict(extra="forbid")
    university_id: str
    tenant_key: str
    overall_status: Literal["PASS", "WARNING", "FAIL"]
    checklist: dict[str, Literal["PASS", "WARNING", "FAIL", "NOT_APPLICABLE"]]
    mapping_coverage: dict[str, float]
    summary_ar: str
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

