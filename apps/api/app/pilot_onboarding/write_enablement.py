"""Dedicated Write Enablement Review and Gate ensuring all 12 criteria pass before write promotion."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class WriteEnablementCheck(BaseModel):
    check_key: str
    title_ar: str
    title_en: str
    status: Literal["PASS", "FAIL", "WARNING"]
    details: str = ""


class WriteEnablementResult(BaseModel):
    pilot_id: UUID
    overall_status: Literal["PASS", "FAIL"]
    can_enable_write: bool
    checks: list[WriteEnablementCheck]
    summary_ar: str


class WriteEnablementGate:
    """Evaluates the 12 strict criteria required to promote a pilot to WRITE_ENABLED_PILOT."""

    @classmethod
    def evaluate(
        cls,
        pilot_id: UUID,
        *,
        has_registration_write_cap: bool,
        has_drop_write_cap: bool,
        idempotency_supported: bool,
        drift_reconciliation_zero_drift: bool,
        integration_audit_active: bool,
        sis_health_healthy: bool,
        registration_window_authoritative: bool,
        section_capacity_authoritative: bool,
        schedule_conflict_authoritative: bool,
        error_contract_validated: bool,
        sandbox_mutation_test_passed: bool,
        explicit_platform_admin_approved: bool,
        notes: str = "",
    ) -> WriteEnablementResult:
        checks: list[WriteEnablementCheck] = []

        # 1. REGISTRATION_WRITE capability
        checks.append(
            WriteEnablementCheck(
                check_key="REGISTRATION_WRITE_CAPABILITY",
                title_ar="دعم صلاحية تسجيل المواد (REGISTRATION_WRITE)",
                title_en="SIS supports REGISTRATION_WRITE capability",
                status="PASS" if has_registration_write_cap else "FAIL",
                details="Authoritative write endpoint confirmed" if has_registration_write_cap else "Missing REGISTRATION_WRITE capability",
            )
        )

        # 2. DROP_WRITE capability
        checks.append(
            WriteEnablementCheck(
                check_key="DROP_WRITE_CAPABILITY",
                title_ar="دعم صلاحية سحب المواد (DROP_WRITE)",
                title_en="SIS supports DROP_WRITE capability",
                status="PASS" if has_drop_write_cap else "FAIL",
                details="Authoritative drop endpoint confirmed" if has_drop_write_cap else "Missing DROP_WRITE capability",
            )
        )

        # 3. Idempotency Key Supported
        checks.append(
            WriteEnablementCheck(
                check_key="IDEMPOTENCY_KEY_SUPPORTED",
                title_ar="دعم مفتاح تكرار الطلبات ومنع العمليات المكررة (Idempotency Key)",
                title_en="SIS enforces idempotency-key handling",
                status="PASS" if idempotency_supported else "FAIL",
                details="Idempotent mutation headers validated" if idempotency_supported else "Idempotency key not enforced by SIS",
            )
        )

        # 4. Drift Reconciliation Verified
        checks.append(
            WriteEnablementCheck(
                check_key="DRIFT_RECONCILIATION_VERIFIED",
                title_ar="التحقق من عدم وجود فروقات في تقرير المطابقة (Zero Drift)",
                title_en="Reconciliation engine confirms zero unhandled drift",
                status="PASS" if drift_reconciliation_zero_drift else "FAIL",
                details="Shadow state matches authoritative SIS" if drift_reconciliation_zero_drift else "Pending reconciliation drift detected",
            )
        )

        # 5. Integration Audit Logging Active
        checks.append(
            WriteEnablementCheck(
                check_key="INTEGRATION_AUDIT_LOGGING_ACTIVE",
                title_ar="تفعيل سجل تدقيق عمليات التكامل والعمليات الحساسة",
                title_en="Audit logging active for all mutation payloads",
                status="PASS" if integration_audit_active else "FAIL",
                details="Audit log ledger active and recording" if integration_audit_active else "Audit trail not active",
            )
        )

        # 6. Current SIS Health Healthy
        checks.append(
            WriteEnablementCheck(
                check_key="SIS_HEALTH_HEALTHY",
                title_ar="حالة الاتصال بالنظام الجامعي سليمة (HEALTHY)",
                title_en="Real-time connectivity probe returns HEALTHY",
                status="PASS" if sis_health_healthy else "FAIL",
                details="Latency within SLA and connectivity confirmed" if sis_health_healthy else "SIS health is degraded or unhealthy",
            )
        )

        # 7. Registration Window Authority
        checks.append(
            WriteEnablementCheck(
                check_key="REGISTRATION_WINDOW_AUTHORITY",
                title_ar="نظام الجامعة هو المرجع الوحيد لفتح وإغلاق فترات التسجيل",
                title_en="SIS maintains strict authority over registration windows",
                status="PASS" if registration_window_authoritative else "FAIL",
                details="Term registration status verified from SIS calendar" if registration_window_authoritative else "Window authority unverified",
            )
        )

        # 8. Section Capacity Authority
        checks.append(
            WriteEnablementCheck(
                check_key="SECTION_CAPACITY_AUTHORITY",
                title_ar="مرجعية المقاعد الشاغرة والطاقة الاستيعابية تعود لنظام الجامعة",
                title_en="SIS is authoritative system of record for section seats",
                status="PASS" if section_capacity_authoritative else "FAIL",
                details="Atomic seat allocation enforced by SIS" if section_capacity_authoritative else "Seat capacity authority unverified",
            )
        )

        # 9. Schedule Conflict Authority
        checks.append(
            WriteEnablementCheck(
                check_key="SCHEDULE_CONFLICT_AUTHORITY",
                title_ar="نظام الجامعة يفحص تعارض المواعيد في الشعب",
                title_en="SIS validates timetable clashes during submission",
                status="PASS" if schedule_conflict_authoritative else "FAIL",
                details="Clash detection enforced by SIS backend" if schedule_conflict_authoritative else "Schedule conflict check unverified",
            )
        )

        # 10. Error Contract Validation
        checks.append(
            WriteEnablementCheck(
                check_key="ERROR_CONTRACT_VALIDATION",
                title_ar="مطابقة عقود أخطاء التسجيل (شعبة مغلقة، متطلب غير مستوفى)",
                title_en="Normalized error codes mapped for registration failures",
                status="PASS" if error_contract_validated else "FAIL",
                details="Standard error envelope contract verified" if error_contract_validated else "Error envelopes not standardized",
            )
        )

        # 11. Safe Sandbox Mutation Testing
        checks.append(
            WriteEnablementCheck(
                check_key="SANDBOX_MUTATION_TESTING",
                title_ar="اجتياز اختبارات التسجيل والسحب الآمنة في البيئة التجريبية",
                title_en="Successful synthetic registration & drop lifecycle in sandbox",
                status="PASS" if sandbox_mutation_test_passed else "FAIL",
                details="End-to-end register and drop flow verified on synthetic student" if sandbox_mutation_test_passed else "Sandbox mutation test failed or unexecuted",
            )
        )

        # 12. Explicit Platform Admin Approval
        checks.append(
            WriteEnablementCheck(
                check_key="PLATFORM_ADMIN_APPROVAL",
                title_ar="موافقة صريحة ومسجلة من مدير منصة مرشدي",
                title_en="Formal written approval recorded from Morshidi Platform Admin",
                status="PASS" if explicit_platform_admin_approved else "FAIL",
                details="Platform administrator authorization confirmed" if explicit_platform_admin_approved else "Awaiting platform admin approval",
            )
        )

        all_passed = all(c.status == "PASS" for c in checks)
        overall = "PASS" if all_passed else "FAIL"

        if all_passed:
            summary_ar = "تم استيفاء جميع معايير تفعيل التسجيل (12/12). الجامعة مؤهلة للتشغيل بنمط الكتابة."
        else:
            failed_count = sum(1 for c in checks if c.status == "FAIL")
            summary_ar = f"فشل اعتماد نمط الكتابة لوجود {failed_count} معايير أساسية غير مستوفاة من أصل 12."

        return WriteEnablementResult(
            pilot_id=pilot_id,
            overall_status=overall,
            can_enable_write=all_passed,
            checks=checks,
            summary_ar=summary_ar,
        )
