"""Domain models and enums for the university pilot engagement, onboarding, and acceptance system."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class PilotStatus(str, Enum):
    """19 deterministic lifecycle states for university pilot onboarding."""

    DRAFT = "DRAFT"
    DISCOVERY = "DISCOVERY"
    WAITING_FOR_UNIVERSITY_IT = "WAITING_FOR_UNIVERSITY_IT"
    TECHNICAL_REQUIREMENTS_RECEIVED = "TECHNICAL_REQUIREMENTS_RECEIVED"
    SANDBOX_PREPARATION = "SANDBOX_PREPARATION"
    IDENTITY_CONFIGURATION = "IDENTITY_CONFIGURATION"
    ACADEMIC_MAPPING = "ACADEMIC_MAPPING"
    SECURITY_REVIEW = "SECURITY_REVIEW"
    TECHNICAL_VALIDATION = "TECHNICAL_VALIDATION"
    READ_ONLY_PILOT_READY = "READ_ONLY_PILOT_READY"
    READ_ONLY_PILOT_ACTIVE = "READ_ONLY_PILOT_ACTIVE"
    READ_ONLY_PILOT_ACCEPTANCE = "READ_ONLY_PILOT_ACCEPTANCE"
    WRITE_PILOT_REVIEW = "WRITE_PILOT_REVIEW"
    WRITE_ENABLED_PILOT_READY = "WRITE_ENABLED_PILOT_READY"
    GO_LIVE_REVIEW = "GO_LIVE_REVIEW"
    ACCEPTED = "ACCEPTED"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"


class PilotMode(str, Enum):
    """Pilot operational mode: Read-Only (default) or Write-Enabled."""

    READ_ONLY_PILOT = "READ_ONLY_PILOT"
    WRITE_ENABLED_PILOT = "WRITE_ENABLED_PILOT"


class StakeholderRole(str, Enum):
    """Operational stakeholder categories for university pilot engagement."""

    MORSHIDI_PLATFORM_ADMIN = "MORSHIDI_PLATFORM_ADMIN"
    UNIVERSITY_TECHNICAL_CONTACT = "UNIVERSITY_TECHNICAL_CONTACT"
    UNIVERSITY_ACADEMIC_CONTACT = "UNIVERSITY_ACADEMIC_CONTACT"
    UNIVERSITY_PILOT_SPONSOR = "UNIVERSITY_PILOT_SPONSOR"
    UNIVERSITY_SECURITY_CONTACT = "UNIVERSITY_SECURITY_CONTACT"
    REGISTRAR_CONTACT = "REGISTRAR_CONTACT"
    NETWORK_CONTACT = "NETWORK_CONTACT"
    IDENTITY_CONTACT = "IDENTITY_CONTACT"


class RequirementCategory(str, Enum):
    """Categories of IT requirements from the institution."""

    SIS_API = "SIS_API"
    IDENTITY_SSO = "IDENTITY_SSO"
    ACADEMIC_DATA = "ACADEMIC_DATA"
    SECURITY = "SECURITY"
    SANDBOX = "SANDBOX"
    NETWORK = "NETWORK"
    LEGAL_OPERATIONAL = "LEGAL_OPERATIONAL"


class RequirementImportance(str, Enum):
    """Importance level for IT requirements."""

    REQUIRED = "REQUIRED"
    OPTIONAL = "OPTIONAL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RequirementStatus(str, Enum):
    """Tracking status for IT requirements."""

    NOT_REQUESTED = "NOT_REQUESTED"
    REQUESTED = "REQUESTED"
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class BlockerSeverity(str, Enum):
    """Severity levels for pilot blockers."""

    SEV1 = "SEV1"  # Critical: blocks all progress, security, identity, cross-tenant
    SEV2 = "SEV2"  # Major: blocks current phase, sync failure, mapping gap
    SEV3 = "SEV3"  # Moderate: non-blocking issue, data discrepancy
    SEV4 = "SEV4"  # Minor: cosmetic, UI, documentation update


class BlockerStatus(str, Enum):
    """Resolution status for pilot blockers."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    WONT_FIX = "WONT_FIX"


class AcceptanceCategory(str, Enum):
    """Categories of pilot acceptance criteria."""

    IDENTITY = "IDENTITY"
    ACADEMIC_DATA = "ACADEMIC_DATA"
    MAPPING = "MAPPING"
    STUDENT_EXPERIENCE = "STUDENT_EXPERIENCE"
    INSTITUTIONAL_EXPERIENCE = "INSTITUTIONAL_EXPERIENCE"
    SECURITY = "SECURITY"
    OPERATIONS = "OPERATIONS"


class AcceptanceStatus(str, Enum):
    """Evaluation status for acceptance criteria."""

    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_TESTED = "NOT_TESTED"


class SignoffRole(str, Enum):
    """Roles authorized to provide pilot operational sign-off."""

    TECHNICAL_SIGN_OFF = "TECHNICAL_SIGN_OFF"
    ACADEMIC_VALIDATION_SIGN_OFF = "ACADEMIC_VALIDATION_SIGN_OFF"
    PILOT_SPONSOR_FINAL_SIGN_OFF = "PILOT_SPONSOR_FINAL_SIGN_OFF"
    MORSHIDI_PLATFORM_SIGN_OFF = "MORSHIDI_PLATFORM_SIGN_OFF"


class SignoffStatus(str, Enum):
    """Sign-off decision status."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ---------------------------------------------------------------------------
# Data Transfer & Entity Models
# ---------------------------------------------------------------------------


class PilotStakeholder(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    pilot_id: UUID
    role: StakeholderRole
    name: str
    title: str = ""
    email: str
    phone: str = ""
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PilotRequirement(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    pilot_id: UUID
    requirement_key: str
    category: RequirementCategory
    title_ar: str
    title_en: str
    importance: RequirementImportance = RequirementImportance.REQUIRED
    status: RequirementStatus = RequirementStatus.NOT_REQUESTED
    secret_ref_name: str | None = None  # Reference to environment variable only
    notes: str = ""
    validated_at: datetime | None = None
    validated_by: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PilotBlocker(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    pilot_id: UUID
    blocker_code: str
    title_ar: str
    severity: BlockerSeverity = BlockerSeverity.SEV2
    owner_role: str = "UNIVERSITY_TECHNICAL_CONTACT"
    status: BlockerStatus = BlockerStatus.OPEN
    resolution_notes: str = ""
    resolved_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PilotAcceptanceCheck(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    pilot_id: UUID
    check_key: str
    category: AcceptanceCategory
    title_ar: str
    title_en: str
    importance: RequirementImportance = RequirementImportance.REQUIRED
    is_automated: bool = False
    status: AcceptanceStatus = AcceptanceStatus.NOT_TESTED
    evidence_ref: str = ""
    tested_by: str = ""
    tested_at: datetime | None = None
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PilotSignoff(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    pilot_id: UUID
    signoff_role: SignoffRole
    signee_name: str
    signee_role: str
    status: SignoffStatus = SignoffStatus.PENDING
    decision_notes: str = ""
    signed_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PilotActivity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    pilot_id: UUID
    action: str
    actor_id: UUID | None = None
    actor_email: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PilotCohortScope(BaseModel):
    """Scope definition targeting specific faculties, majors, plans, and terms."""

    faculties: list[str] = Field(default_factory=list)
    majors: list[str] = Field(default_factory=list)
    academic_plans: list[str] = Field(default_factory=list)
    target_terms: list[str] = Field(default_factory=list)
    estimated_student_count: int = 0
    scope_notes: str = ""


class DiscoveryIntake(BaseModel):
    """Structured intake captured during initial discovery with University IT."""

    university_name_official: str = ""
    country: str = "Jordan"
    timezone: str = "Asia/Amman"
    preferred_locale: str = "ar"
    sis_vendor: str = ""  # e.g. "Ellucian Banner", "Oracle PeopleSoft", "In-House Custom"
    hosting_model: str = "ON_PREMISE"  # "ON_PREMISE", "CLOUD_SAAS", "HYBRID"
    api_available: bool = False
    api_version: str = "v1"
    sandbox_available: bool = False
    documentation_available: bool = False
    identity_protocol: str = "OIDC"  # "OIDC", "SAML", "TOKEN_EXCHANGE", "LOCAL"
    academic_structure_summary: str = ""
    network_restrictions: str = ""
    notes: str = ""


class UniversityPilot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    university_id: UUID
    pilot_name: str
    status: PilotStatus = PilotStatus.DRAFT
    mode: PilotMode = PilotMode.READ_ONLY_PILOT
    target_start_date: date | None = None
    target_end_date: date | None = None
    cohort_scope: PilotCohortScope = Field(default_factory=PilotCohortScope)
    discovery_intake: DiscoveryIntake = Field(default_factory=DiscoveryIntake)
    technical_questionnaire: dict[str, Any] = Field(default_factory=dict)
    security_questionnaire: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PilotSummary(BaseModel):
    """Deterministic summary metrics for pilot dashboard and report."""

    pilot_id: UUID
    pilot_name: str
    status: PilotStatus
    mode: PilotMode
    current_phase: str
    technical_readiness_score: str  # e.g. "15/16 PASS"
    operational_readiness_score: str  # e.g. "18/20 PASS"
    mapping_coverage_pct: float
    open_critical_blockers_count: int
    open_total_blockers_count: int
    requirements_validated_count: int
    requirements_total_count: int
    acceptance_passed_count: int
    acceptance_total_count: int
    last_sync_status: str | None = None
    target_start_date: date | None = None
    target_end_date: date | None = None


class PilotReport(BaseModel):
    """Structured pilot acceptance report."""

    pilot_id: UUID
    university_id: UUID
    university_name: str
    pilot_name: str
    mode: PilotMode
    status: PilotStatus
    technical_readiness: dict[str, Any]
    mapping_coverage: dict[str, float]
    sync_health: dict[str, Any]
    security_status: dict[str, Any]
    acceptance_results: dict[str, Any]
    open_blockers: list[dict[str, Any]]
    signoffs: list[dict[str, Any]]
    final_recommendation: Literal["ACCEPTED", "ACCEPTED_WITH_WARNINGS", "BLOCKED"]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
