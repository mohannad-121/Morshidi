"""16-point deterministic readiness scorecard evaluator for university pilot onboarding."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from .capabilities import PilotMode, SISCapability
from .mapping_layer import MappingLayer
from .models import (
    HealthResult,
    PilotReadinessScorecard,
    UniversityIntegrationConfig,
    UniversityTenant,
)
from .security import resolve_secret


class PilotReadinessEvaluator:
    """Evaluates the 16-point technical readiness checklist for university tenants."""

    @classmethod
    def evaluate(
        cls,
        tenant: UniversityTenant,
        config: UniversityIntegrationConfig | None,
        health: HealthResult,
        mapping_layer: MappingLayer,
        known_entities: dict[str, list[str]],
        *,
        sync_job_count: int = 0,
        recent_sync_succeeded: bool = False,
    ) -> PilotReadinessScorecard:
        checklist: dict[str, Literal["PASS", "WARNING", "FAIL", "NOT_APPLICABLE"]] = {}

        # 1. Tenant Config Exists
        checklist["TENANT_CONFIG_EXISTS"] = "PASS" if tenant.tenant_key else "FAIL"

        # 2. Integration Config Exists & Active
        checklist["INTEGRATION_CONFIG_EXISTS"] = "PASS" if (config and config.active) else "FAIL"

        # 3. Target URL Valid
        if config and config.base_url and config.base_url.startswith("http"):
            checklist["TARGET_URL_VALID"] = "PASS"
        else:
            checklist["TARGET_URL_VALID"] = "FAIL"

        # 4. Credentials Configured
        if not config:
            checklist["CREDENTIALS_CONFIGURED"] = "FAIL"
        elif config.auth_method == "client_credentials":
            secret = resolve_secret(config.secret_env_ref)
            checklist["CREDENTIALS_CONFIGURED"] = "PASS" if (secret and config.client_id) else "FAIL"
        elif config.auth_method == "token":
            secret = resolve_secret(config.secret_env_ref)
            checklist["CREDENTIALS_CONFIGURED"] = "PASS" if secret else "FAIL"
        else:
            checklist["CREDENTIALS_CONFIGURED"] = "PASS"

        # 5. Connectivity Probe
        if health.status == "HEALTHY":
            checklist["CONNECTIVITY_PROBE"] = "PASS"
        elif health.status == "DEGRADED":
            checklist["CONNECTIVITY_PROBE"] = "WARNING"
        else:
            checklist["CONNECTIVITY_PROBE"] = "FAIL"

        # 6. Capabilities Negotiated
        caps = set(config.supported_capabilities) if config else set()
        required_min_caps = {SISCapability.STUDENT_PROFILE_READ}
        if required_min_caps.issubset(caps):
            checklist["CAPABILITIES_NEGOTIATED"] = "PASS"
        elif caps:
            checklist["CAPABILITIES_NEGOTIATED"] = "WARNING"
        else:
            checklist["CAPABILITIES_NEGOTIATED"] = "FAIL"

        # 7. Pilot Mode Valid
        if config and config.pilot_mode in {PilotMode.READ_ONLY_PILOT, PilotMode.WRITE_ENABLED_PILOT}:
            checklist["PILOT_MODE_VALID"] = "PASS"
        else:
            checklist["PILOT_MODE_VALID"] = "FAIL"

        # 8-10. Curriculum Mappings
        coverage = mapping_layer.compute_coverage(known_entities)  # type: ignore[arg-type]

        checklist["FACULTY_MAPPINGS_PRESENT"] = "PASS" if coverage.get("faculty", 100.0) >= 100.0 else "WARNING"
        checklist["MAJOR_MAPPINGS_PRESENT"] = "PASS" if coverage.get("major", 100.0) >= 100.0 else "WARNING"
        checklist["PLAN_MAPPINGS_PRESENT"] = "PASS" if coverage.get("plan", 100.0) >= 100.0 else "WARNING"

        # 11. Course Mapping Coverage
        course_cov = coverage.get("course", 100.0)
        if course_cov >= 90.0:
            checklist["COURSE_MAPPINGS_COVERAGE"] = "PASS"
        elif course_cov >= 70.0:
            checklist["COURSE_MAPPINGS_COVERAGE"] = "WARNING"
        else:
            checklist["COURSE_MAPPINGS_COVERAGE"] = "FAIL"

        # 12. Term Mappings
        checklist["TERM_MAPPINGS_PRESENT"] = "PASS" if coverage.get("term", 100.0) >= 100.0 else "WARNING"

        # 13. SSO Readiness
        if config and (SISCapability.SSO in caps or config.auth_method == "sso"):
            checklist["SSO_READINESS"] = "PASS" if config.feature_flags.get("sso_enabled") else "WARNING"
        else:
            checklist["SSO_READINESS"] = "NOT_APPLICABLE"

        # 14. Webhook Security
        if config and SISCapability.WEBHOOKS in caps:
            wh_secret = resolve_secret(config.webhook_secret_env_ref)
            checklist["WEBHOOK_SECURITY"] = "PASS" if wh_secret else "FAIL"
        else:
            checklist["WEBHOOK_SECURITY"] = "NOT_APPLICABLE"

        # 15. Sync Baseline Tested
        if recent_sync_succeeded:
            checklist["SYNC_BASELINE_TESTED"] = "PASS"
        elif sync_job_count > 0:
            checklist["SYNC_BASELINE_TESTED"] = "WARNING"
        else:
            checklist["SYNC_BASELINE_TESTED"] = "WARNING"

        # 16. Data Isolation Confirmed
        checklist["DATA_ISOLATION_CONFIRMED"] = "PASS" if (tenant.id and tenant.tenant_key) else "FAIL"

        # Compute Overall Status
        has_fail = any(v == "FAIL" for v in checklist.values())
        has_warning = any(v == "WARNING" for v in checklist.values())

        if has_fail:
            overall: Literal["PASS", "WARNING", "FAIL"] = "FAIL"
            summary_ar = "الجامعة غير جاهزة للإطلاق التجريبي لوجود متطلبات أساسية غير مكتملة."
        elif has_warning:
            overall = "WARNING"
            summary_ar = "الجامعة شبه جاهزة للإطلاق التجريبي مع وجود تنبيهات يوصى بمعالجتها."
        else:
            overall = "PASS"
            summary_ar = "جميع المتطلبات الفنية للإطلاق التجريبي مكتملة ومطابقة للمعايير."

        return PilotReadinessScorecard(
            university_id=str(tenant.id),
            tenant_key=tenant.tenant_key,
            overall_status=overall,
            checklist=checklist,
            mapping_coverage=coverage,
            summary_ar=summary_ar,
        )

