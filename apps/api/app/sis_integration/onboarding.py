"""University Onboarding Specification, Validation, and Diagnostics Engine.

Provides automated preflight checks, configuration validation, capability auditing,
and actionable onboarding diagnostics to onboard new universities without code changes.

Principle: THE UNIVERSITY SIS REMAINS AUTHORITATIVE. AI EXPLAINS — DETERMINISTIC RULES DECIDE.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.university_sync.grading_policy import (
    GradingScaleType,
    SUPPORTED_POLICY_VERSIONS,
    create_standard_policy,
)

from .capabilities import PilotMode, SISCapability, TenantStatus, CapabilityNegotiator
from .models import (
    HealthResult,
    UniversityIntegrationConfig,
    UniversityMapping,
    UniversityTenant,
)
from .security import validate_target_url


class FacultySpec(BaseModel):
    code: str = Field(min_length=1)
    name_ar: str = Field(min_length=1)
    name_en: str | None = None


class MajorSpec(BaseModel):
    code: str = Field(min_length=1)
    faculty_code: str = Field(min_length=1)
    name_ar: str = Field(min_length=1)
    name_en: str | None = None
    degree: str = "BACHELOR"


class CampusSpec(BaseModel):
    code: str = Field(min_length=1)
    name_ar: str = Field(min_length=1)
    name_en: str | None = None
    city: str | None = None
    is_main: bool = False


class InstitutionalHierarchySpec(BaseModel):
    faculties: list[FacultySpec] = Field(default_factory=list)
    majors: list[MajorSpec] = Field(default_factory=list)
    campuses: list[CampusSpec] = Field(default_factory=list)


class GradingPolicyConfigSpec(BaseModel):
    policy_version: str = "UNIVERSAL_PERCENTAGE_100_V1"
    scale_type: GradingScaleType = GradingScaleType.PERCENTAGE_100
    gpa_scale: Decimal = Decimal("100.00")
    gpa_min: Decimal = Decimal("0.00")
    gpa_max: Decimal = Decimal("100.00")
    course_grade_min: Decimal = Decimal("0.00")
    course_grade_max: Decimal = Decimal("100.00")
    passing_grade: Decimal = Decimal("50.00")
    major_passing_grade: Decimal = Decimal("60.00")
    warning_threshold: Decimal = Decimal("60.00")
    honors_threshold: Decimal = Decimal("84.00")
    letter_grade_mappings: list[dict[str, Any]] = Field(default_factory=list)


class InitialMappingSpec(BaseModel):
    entity_type: Literal["FACULTY", "MAJOR", "PLAN", "COURSE", "TERM", "SECTION", "COURSE_ALIAS"]
    external_code: str = Field(min_length=1)
    canonical_id: str = Field(min_length=1)
    canonical_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CourseAliasSpec(BaseModel):
    canonical_course_code: str = Field(min_length=1)
    alias_name_ar: str = Field(min_length=1)
    alias_name_en: str | None = None
    alias_code: str | None = None
    alias_type: str = "INSTITUTIONAL_NAME"
    is_verified: bool = True
    notes: str | None = None


class UniversityOnboardingSpec(BaseModel):
    """Complete onboarding specification for a new university."""

    model_config = ConfigDict(extra="ignore")

    name_ar: str = Field(min_length=2)
    name_en: str | None = None
    tenant_key: str = Field(min_length=2)
    country: str = "JO"
    timezone: str = "Asia/Amman"
    default_locale: str = "ar"
    adapter_provider_type: str = "generic_rest"
    base_url: str = Field(min_length=4)
    auth_method: str = "client_credentials"
    client_id: str | None = None
    secret_env_ref: str | None = None
    token_url: str | None = None
    api_version: str = "v1"
    supported_capabilities: list[SISCapability] = Field(default_factory=list)
    pilot_mode: PilotMode = PilotMode.READ_ONLY_PILOT
    hierarchy: InstitutionalHierarchySpec = Field(default_factory=InstitutionalHierarchySpec)
    grading_policy: GradingPolicyConfigSpec = Field(default_factory=GradingPolicyConfigSpec)
    initial_mappings: list[InitialMappingSpec] = Field(default_factory=list)
    course_aliases: list[CourseAliasSpec] = Field(default_factory=list)


class OnboardingValidationResult(BaseModel):
    valid: bool
    tenant_key: str
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    capabilities_declared: list[str] = Field(default_factory=list)
    degradation_summary: dict[str, Any] = Field(default_factory=dict)
    readiness_stage: str = "DRAFT"


class DiagnosticCheckResult(BaseModel):
    name: str
    status: Literal["PASS", "WARNING", "FAIL", "SKIPPED"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class OnboardingDiagnosticsReport(BaseModel):
    university_id: str
    tenant_key: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overall_readiness: Literal["READY", "NEEDS_ATTENTION", "BLOCKED"]
    checks: list[DiagnosticCheckResult]
    capability_coverage: dict[str, Any]
    mapping_statistics: dict[str, int]
    recommendations_ar: list[str]
    recommendations_en: list[str]


class OnboardingDiagnosticsEngine:
    """Audits configurations, connectivity, capabilities, and mappings for institutional onboarding."""

    @staticmethod
    def validate_spec(spec: UniversityOnboardingSpec, allow_localhost: bool = False) -> OnboardingValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Tenant key format
        if not re.fullmatch(r"^[a-z0-9_-]{2,32}$", spec.tenant_key):
            errors.append("tenant_key must consist of lowercase alphanumeric characters, underscores, or hyphens (2-32 chars)")

        # 2. SSRF validation for base_url
        try:
            validate_target_url(spec.base_url, allow_localhost=allow_localhost)
        except Exception as err:
            errors.append(f"Invalid base_url: {err}")

        # 3. Auth configuration
        if spec.auth_method == "client_credentials" and not spec.client_id and spec.adapter_provider_type != "fake_university":
            warnings.append("client_credentials auth method specified without client_id")

        if not spec.secret_env_ref and spec.adapter_provider_type != "fake_university":
            warnings.append("secret_env_ref is not specified; external calls may fail if authentication is required")

        # 4. Capabilities evaluation
        caps = set(spec.supported_capabilities)
        if SISCapability.IDENTITY_AUTH not in caps:
            errors.append("IDENTITY_AUTH capability is mandatory for student login and synchronization")

        if SISCapability.STUDENT_PROFILE_READ not in caps:
            errors.append("STUDENT_PROFILE_READ capability is mandatory for academic profile loading")

        if spec.pilot_mode == PilotMode.WRITE_ENABLED_PILOT and SISCapability.REGISTRATION_WRITE not in caps:
            errors.append("WRITE_ENABLED_PILOT requested but REGISTRATION_WRITE capability is missing")

        # 5. Grading policy validation
        gp = spec.grading_policy
        if gp.gpa_min >= gp.gpa_max:
            errors.append("Grading policy gpa_min must be strictly less than gpa_max")
        if gp.course_grade_min >= gp.course_grade_max:
            errors.append("Grading policy course_grade_min must be strictly less than course_grade_max")
        if gp.passing_grade < gp.course_grade_min or gp.passing_grade > gp.course_grade_max:
            errors.append("Grading policy passing_grade must fall within course grade bounds")
        if gp.major_passing_grade < gp.passing_grade:
            warnings.append("Grading policy major_passing_grade is lower than passing_grade; typically major courses require higher or equal grade")

        # 6. Degradation analysis
        degradation = CapabilityNegotiator.evaluate_feature_degradation(caps)

        # 7. Hierarchy completeness
        faculty_codes = {f.code.strip().upper() for f in spec.hierarchy.faculties}
        for major in spec.hierarchy.majors:
            if major.faculty_code.strip().upper() not in faculty_codes and faculty_codes:
                warnings.append(f"Major '{major.code}' references unknown faculty code '{major.faculty_code}'")

        readiness_stage = "PILOT_READY" if not errors and not warnings else ("CONFIGURING" if not errors else "DRAFT")

        return OnboardingValidationResult(
            valid=len(errors) == 0,
            tenant_key=spec.tenant_key,
            errors=errors,
            warnings=warnings,
            capabilities_declared=[c.value for c in spec.supported_capabilities],
            degradation_summary=degradation,
            readiness_stage=readiness_stage,
        )

    @staticmethod
    def evaluate_live_readiness(
        tenant: UniversityTenant,
        config: UniversityIntegrationConfig | None,
        health: HealthResult,
        declared_capabilities: set[SISCapability],
        mappings_by_type: dict[str, int],
        has_grading_policy: bool = True,
    ) -> OnboardingDiagnosticsReport:
        checks: list[DiagnosticCheckResult] = []
        recommendations_ar: list[str] = []
        recommendations_en: list[str] = []

        # 1. Tenant Status
        if tenant.status == TenantStatus.ACTIVE or tenant.status == TenantStatus.PILOT_READY:
            checks.append(DiagnosticCheckResult(
                name="TENANT_STATUS",
                status="PASS",
                message=f"Tenant status is active/ready ({tenant.status.value})",
            ))
        else:
            checks.append(DiagnosticCheckResult(
                name="TENANT_STATUS",
                status="WARNING",
                message=f"Tenant is currently in {tenant.status.value} stage",
            ))

        # 2. Config check
        if config and config.active:
            checks.append(DiagnosticCheckResult(
                name="INTEGRATION_CONFIG",
                status="PASS",
                message=f"Integration configuration active for provider '{config.provider_type}'",
                details={"provider": config.provider_type, "base_url": config.base_url},
            ))
        else:
            checks.append(DiagnosticCheckResult(
                name="INTEGRATION_CONFIG",
                status="FAIL",
                message="Integration configuration missing or inactive",
            ))
            recommendations_ar.append("تكوين إعدادات الربط مع نظام معلومات الطلبة (SIS) وتفعيل المزود.")
            recommendations_en.append("Configure and activate SIS integration settings.")

        # 3. Health & Connectivity
        if health.status == "HEALTHY":
            checks.append(DiagnosticCheckResult(
                name="CONNECTIVITY",
                status="PASS",
                message=f"SIS endpoint reachable (latency: {health.latency_ms}ms)",
            ))
        elif health.status == "DEGRADED":
            checks.append(DiagnosticCheckResult(
                name="CONNECTIVITY",
                status="WARNING",
                message=f"SIS connectivity degraded: {health.details}",
            ))
        else:
            checks.append(DiagnosticCheckResult(
                name="CONNECTIVITY",
                status="FAIL",
                message=f"SIS endpoint unreachable: {health.details.get('error', 'unknown error')}",
            ))
            recommendations_ar.append("التحقق من جدار الحماية ونقطة نهاية الـ API الخاصة بالجامعة.")
            recommendations_en.append("Verify network connectivity and SIS API endpoint reachability.")

        # 4. Mandatory Capabilities
        missing_mandatory = []
        if SISCapability.IDENTITY_AUTH not in declared_capabilities:
            missing_mandatory.append("IDENTITY_AUTH")
        if SISCapability.STUDENT_PROFILE_READ not in declared_capabilities:
            missing_mandatory.append("STUDENT_PROFILE_READ")

        if not missing_mandatory:
            checks.append(DiagnosticCheckResult(
                name="MANDATORY_CAPABILITIES",
                status="PASS",
                message="All mandatory capabilities are declared and active",
            ))
        else:
            checks.append(DiagnosticCheckResult(
                name="MANDATORY_CAPABILITIES",
                status="FAIL",
                message=f"Missing mandatory capabilities: {', '.join(missing_mandatory)}",
            ))
            recommendations_ar.append(f"تفعيل الصلاحيات الإلزامية: {', '.join(missing_mandatory)}")
            recommendations_en.append(f"Enable mandatory capabilities: {', '.join(missing_mandatory)}")

        # 5. Mapping Coverage
        course_count = mappings_by_type.get("COURSE", 0)
        plan_count = mappings_by_type.get("PLAN", 0)
        faculty_count = mappings_by_type.get("FACULTY", 0)

        if course_count > 0 and plan_count > 0:
            checks.append(DiagnosticCheckResult(
                name="MAPPING_COVERAGE",
                status="PASS",
                message=f"Found {course_count} course mappings and {plan_count} study plan mappings",
                details=mappings_by_type,
            ))
        else:
            checks.append(DiagnosticCheckResult(
                name="MAPPING_COVERAGE",
                status="WARNING",
                message=f"Low mapping count: {course_count} courses, {plan_count} plans mapped",
                details=mappings_by_type,
            ))
            recommendations_ar.append("استيراد وربط رموز الخطط الدراسية والمواد في جدول المطابقات.")
            recommendations_en.append("Import and map study plans and course codes into university mappings.")

        # 6. Grading Policy
        if has_grading_policy:
            checks.append(DiagnosticCheckResult(
                name="GRADING_POLICY",
                status="PASS",
                message="Institutional grading policy configured",
            ))
        else:
            checks.append(DiagnosticCheckResult(
                name="GRADING_POLICY",
                status="WARNING",
                message="No explicit grading policy configured; falling back to default percentage scale",
            ))

        # Overall Status
        has_fail = any(c.status == "FAIL" for c in checks)
        has_warn = any(c.status == "WARNING" for c in checks)
        overall: Literal["READY", "NEEDS_ATTENTION", "BLOCKED"] = (
            "BLOCKED" if has_fail else ("NEEDS_ATTENTION" if has_warn else "READY")
        )

        return OnboardingDiagnosticsReport(
            university_id=str(tenant.id),
            tenant_key=tenant.tenant_key,
            overall_readiness=overall,
            checks=checks,
            capability_coverage=CapabilityNegotiator.evaluate_feature_degradation(declared_capabilities),
            mapping_statistics=mappings_by_type,
            recommendations_ar=recommendations_ar,
            recommendations_en=recommendations_en,
        )
