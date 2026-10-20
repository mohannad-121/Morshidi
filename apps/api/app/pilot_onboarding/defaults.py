"""Default catalogs, templates, and questionnaires for university pilot onboarding."""

from __future__ import annotations

from typing import Any

from .models import (
    AcceptanceCategory,
    RequirementCategory,
    RequirementImportance,
)

# ---------------------------------------------------------------------------
# 1. Standard IT Requirements Catalog (Section 9)
# ---------------------------------------------------------------------------

DEFAULT_IT_REQUIREMENTS = [
    # SIS API
    {
        "requirement_key": "SIS_API_DOCUMENTATION",
        "category": RequirementCategory.SIS_API,
        "title_ar": "وثائق واجهات برمجة التطبيقات (API Documentation)",
        "title_en": "SIS REST API Documentation / Swagger / OpenAPI spec",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "SANDBOX_BASE_URL",
        "category": RequirementCategory.SANDBOX,
        "title_ar": "عنوان البيئة التجريبية للجامعة (Sandbox Base URL)",
        "title_en": "University Sandbox Gateway Base URL",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "AUTH_METHOD_DOCUMENTATION",
        "category": RequirementCategory.SIS_API,
        "title_ar": "بروتوكول التوثيق للربط (Client Credentials / Bearer Token)",
        "title_en": "API Authentication Method Specification",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "API_CREDENTIALS_PROVISIONED",
        "category": RequirementCategory.SIS_API,
        "title_ar": "إنشاء حساب واعتماد للربط في البيئة التجريبية",
        "title_en": "API Client ID & Secret provisioned for Sandbox",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "API_RATE_LIMITS",
        "category": RequirementCategory.SIS_API,
        "title_ar": "حدود الاستهلاك والطلبات (Rate Limits / Quotas)",
        "title_en": "Documented Rate Limits and Request Caps",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "FIELD_DICTIONARY",
        "category": RequirementCategory.ACADEMIC_DATA,
        "title_ar": "قاموس البيانات والحقول الأكاديمية (Data Dictionary)",
        "title_en": "University Academic Field Dictionary",
        "importance": RequirementImportance.REQUIRED,
    },
    # Identity & SSO
    {
        "requirement_key": "OIDC_SAML_METADATA",
        "category": RequirementCategory.IDENTITY_SSO,
        "title_ar": "بيانات وصفية لمزود الهوية (IdP Metadata / Discovery URL)",
        "title_en": "IdP Metadata XML or OIDC Well-Known URL",
        "importance": RequirementImportance.OPTIONAL,
    },
    {
        "requirement_key": "SSO_CLAIM_MAPPING",
        "category": RequirementCategory.IDENTITY_SSO,
        "title_ar": "تحديد حقل الرقم الجامعي في رمز الدخول (Student ID Claim)",
        "title_en": "Mapped Student ID & Email Claims specification",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "SANDBOX_TEST_STUDENTS",
        "category": RequirementCategory.SANDBOX,
        "title_ar": "قائمة حسابات طلابية وهمية للاختبار (Test Identities)",
        "title_en": "Synthetic Test Student Accounts Matrix",
        "importance": RequirementImportance.REQUIRED,
    },
    # Academic Data Exports / Structure
    {
        "requirement_key": "FACULTY_CODES_LIST",
        "category": RequirementCategory.ACADEMIC_DATA,
        "title_ar": "قائمة رموز الكليات الرسمية (Faculty Codes)",
        "title_en": "Official Faculty / College Codes Reference",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "MAJOR_CODES_LIST",
        "category": RequirementCategory.ACADEMIC_DATA,
        "title_ar": "قائمة رموز التخصصات (Major / Program Codes)",
        "title_en": "Academic Majors / Programs Codes Reference",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "PLAN_CODES_LIST",
        "category": RequirementCategory.ACADEMIC_DATA,
        "title_ar": "رموز وإصدارات الخطط الدراسية (Study Plan Versions)",
        "title_en": "Study Plan Numbers / Version Identifiers",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "COURSE_CATALOG_EXPORT",
        "category": RequirementCategory.ACADEMIC_DATA,
        "title_ar": "كتالوج المواد الأكاديمية ونظام الساعات (Course Catalog)",
        "title_en": "Course Catalog Export with Credit Hours",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "TERM_CODES_LIST",
        "category": RequirementCategory.ACADEMIC_DATA,
        "title_ar": "رموز الفصول والتقويم الأكاديمي (Academic Terms)",
        "title_en": "Academic Calendar & Term Identifiers",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "GRADING_SCALE_POLICY",
        "category": RequirementCategory.ACADEMIC_DATA,
        "title_ar": "سياسة وعلامات التقييم والنجاح (Grading Scale & Policy)",
        "title_en": "Grading Scale (0-100 or 4.0), Pass Marks, and GPA weights",
        "importance": RequirementImportance.REQUIRED,
    },
    # Webhooks & Sync
    {
        "requirement_key": "WEBHOOK_EVENT_SUPPORT",
        "category": RequirementCategory.SIS_API,
        "title_ar": "دعم إرسال إشعارات التغييرات (Webhooks / Real-Time Events)",
        "title_en": "Inbound Webhook Support Specification",
        "importance": RequirementImportance.OPTIONAL,
    },
    # Network & Security
    {
        "requirement_key": "IP_ALLOWLIST_CONFIGURED",
        "category": RequirementCategory.NETWORK,
        "title_ar": "السماح لعناوين IP لخوادم مرشدي بالوصول للبيئة التجريبية",
        "title_en": "Morshidi Outbound IPs Allowlisted in University Firewall",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "TLS_13_COMPLIANCE",
        "category": RequirementCategory.SECURITY,
        "title_ar": "تشفير الاتصال بشهادة موثوقة (TLS 1.2+ / HTTPS)",
        "title_en": "TLS 1.2+ HTTPS Endpoints with Valid CA Certificate",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "SECURITY_REVIEW_COMPLETED",
        "category": RequirementCategory.SECURITY,
        "title_ar": "إتمام استبيان الأمان التقني ومراجعة حماية البيانات",
        "title_en": "Technical Security Questionnaire Evaluated",
        "importance": RequirementImportance.REQUIRED,
    },
    # Legal & Operational
    {
        "requirement_key": "PILOT_COHORT_APPROVAL",
        "category": RequirementCategory.LEGAL_OPERATIONAL,
        "title_ar": "اعتماد نطاق الدفعة التجريبية (الكليات والتخصصات)",
        "title_en": "Pilot Cohort Scope Formally Approved by Sponsor",
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "requirement_key": "ESCALATION_CONTACTS_EXCHANGED",
        "category": RequirementCategory.LEGAL_OPERATIONAL,
        "title_ar": "تحديد جهات الاتصال للدعم الفني والطارئ (SEV1-SEV4)",
        "title_en": "Support Escalation Contacts Exchanged",
        "importance": RequirementImportance.REQUIRED,
    },
]

# ---------------------------------------------------------------------------
# 2. Standard Pilot Acceptance Checks (Section 22)
# ---------------------------------------------------------------------------

DEFAULT_ACCEPTANCE_CHECKS = [
    # 1. Identity
    {
        "check_key": "IDENTITY_RESOLUTION",
        "category": AcceptanceCategory.IDENTITY,
        "title_ar": "التحقق من صحة ربط هوية الطالب وعدم وجود لبس",
        "title_en": "Student Identity Resolution and Zero-Ambiguity Linking",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "TENANT_ASSIGNMENT",
        "category": AcceptanceCategory.IDENTITY,
        "title_ar": "تخصيص الطالب للمستأجر الجامعي الصحيح وعزل البيانات",
        "title_en": "Strict Tenant Assignment and Data Isolation",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    # 2. Academic Data
    {
        "check_key": "PROFILE_SYNC_CONSISTENCY",
        "category": AcceptanceCategory.ACADEMIC_DATA,
        "title_ar": "مطابقة بيانات الملف الأكاديمي (الاسم، الكلية، التخصص)",
        "title_en": "Profile Sync Consistency with Authoritative SIS",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "GRADES_SYNC_ACCURACY",
        "category": AcceptanceCategory.ACADEMIC_DATA,
        "title_ar": "دقة سجل العلامات والمعدل التراكمي ومطابقتها للمصدر",
        "title_en": "Grades & GPA Sync Accuracy without Deviation",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "ENROLLMENTS_CONSISTENCY",
        "category": AcceptanceCategory.ACADEMIC_DATA,
        "title_ar": "مطابقة التسجيلات الحالية والشعب الدراسية",
        "title_en": "Current Enrollments Consistency with SIS",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "STUDY_PLAN_RESOLVED",
        "category": AcceptanceCategory.ACADEMIC_DATA,
        "title_ar": "تحديد الخطة الدراسية بدقة لطلبة الدفعة التجريبية",
        "title_en": "Authoritative Study Plan Resolution",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    # 3. Mapping
    {
        "check_key": "COHORT_PLANS_MAPPED",
        "category": AcceptanceCategory.MAPPING,
        "title_ar": "اكتمال مطابقة جميع خطط الدفعة التجريبية بنسبة 100%",
        "title_en": "100% Mapping Coverage for Pilot Cohort Study Plans",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "COHORT_COURSES_MAPPED",
        "category": AcceptanceCategory.MAPPING,
        "title_ar": "تحقيق نسبة مطابقة مواد لا تقل عن 90% للمواد المعنية",
        "title_en": "At least 90% Course Mapping Coverage for Active Cohort",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "NO_UNRESOLVED_CRITICAL_MAPPINGS",
        "category": AcceptanceCategory.MAPPING,
        "title_ar": "انعدام الكيانات الأساسية المجهولة أو غير المطابقة",
        "title_en": "Zero Unresolved Critical Faculty/Major/Course Mappings",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    # 4. Student Experience
    {
        "check_key": "STUDENT_LOGIN_VERIFIED",
        "category": AcceptanceCategory.STUDENT_EXPERIENCE,
        "title_ar": "نجاح تسجيل دخول الطالب عبر نظام الجامعة أو الرمز التجريبي",
        "title_en": "Student Login via University Identity or Test Auth",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "ELIGIBILITY_DETERMINISTIC",
        "category": AcceptanceCategory.STUDENT_EXPERIENCE,
        "title_ar": "محرك الأهلية يعطي نتائج حتمية مطابقة لقواعد الكلية",
        "title_en": "Deterministic Prerequisite & Eligibility Evaluation",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "PLANNER_AND_DEGREE_PATH",
        "category": AcceptanceCategory.STUDENT_EXPERIENCE,
        "title_ar": "عمل المخطط الفصلي ومسار التخرج بدقة وبدون أخطاء",
        "title_en": "Semester Planner and Degree Path Functionality",
        "is_automated": False,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "STUDENT_INTELLIGENCE_FUNCTIONAL",
        "category": AcceptanceCategory.STUDENT_EXPERIENCE,
        "title_ar": "عمل أسئلة الاختبار السريع ومؤشرات المهارات الخاصة بالتخصص",
        "title_en": "Curriculum-Specific Diagnostics & Skill Bridge Active",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "ADVISOR_COPILOT_GROUNDED",
        "category": AcceptanceCategory.STUDENT_EXPERIENCE,
        "title_ar": "إجابات المرشد الأكاديمي مسندة لأدلة رسمية ولا تفتعل قرارات",
        "title_en": "Advisor Guidance Strictly Grounded in Governed Evidence",
        "is_automated": False,
        "importance": RequirementImportance.REQUIRED,
    },
    # 5. Institutional Experience
    {
        "check_key": "INSTITUTIONAL_OVERVIEW_CORRECT",
        "category": AcceptanceCategory.INSTITUTIONAL_EXPERIENCE,
        "title_ar": "دقة لوحة الذكاء المؤسسي ومؤشرات البرامج الأكاديمية",
        "title_en": "Institutional Analytics Overview and Program KPIs Accurate",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "DEMAND_AND_BOTTLENECK_GROUNDED",
        "category": AcceptanceCategory.INSTITUTIONAL_EXPERIENCE,
        "title_ar": "تحليلات الطلب على المواد والاختناقات مستندة لحسابات دقيقة",
        "title_en": "Course Demand and Bottlenecks Formally Grounded",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    # 6. Security & Invariants
    {
        "check_key": "ZERO_CROSS_TENANT_LEAKAGE",
        "category": AcceptanceCategory.SECURITY,
        "title_ar": "انعدام تسريب البيانات بين الجامعات (Zero Cross-Tenant Leakage)",
        "title_en": "Physical Cross-Tenant Data Isolation Verified (0 Leakage)",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "ZERO_SECRET_EXPOSURE",
        "category": AcceptanceCategory.SECURITY,
        "title_ar": "عدم كشف أي مفاتيح أو كلمات مرور في واجهات برمجة التطبيقات",
        "title_en": "Zero Plaintext Secret Exposure in APIs or Metadata",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "READ_ONLY_MODE_WRITE_BLOCKED",
        "category": AcceptanceCategory.SECURITY,
        "title_ar": "حظر عمليات التعديل والتسجيل في نمط القراءة فقط الصارم",
        "title_en": "Strict Write Operation Blocking in READ_ONLY_PILOT Mode",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    # 7. Operations & Support
    {
        "check_key": "SYNC_AND_RECONCILIATION_HEALTHY",
        "category": AcceptanceCategory.OPERATIONS,
        "title_ar": "سلامة عمليات المزامنة واستقرار تقارير الفروقات",
        "title_en": "Sync Latency Acceptable and Reconciliation Contained",
        "is_automated": True,
        "importance": RequirementImportance.REQUIRED,
    },
    {
        "check_key": "SUPPORT_ESCALATION_VALIDATED",
        "category": AcceptanceCategory.OPERATIONS,
        "title_ar": "جاهزية قنوات الدعم الفني المشترك وإجراءات الطوارئ",
        "title_en": "Operational Escalation Matrix and Incident Channels Ready",
        "is_automated": False,
        "importance": RequirementImportance.REQUIRED,
    },
]

# ---------------------------------------------------------------------------
# 3. Technical Questionnaire (Sections A through M) (Section 11)
# ---------------------------------------------------------------------------

TECHNICAL_QUESTIONNAIRE_SCHEMA = {
    "sections": [
        {"id": "A", "title_en": "SIS Architecture", "title_ar": "بنية نظام معلومات الطلبة (SIS)"},
        {"id": "B", "title_en": "Authentication & Credentials", "title_ar": "التوثيق وبيانات الاعتماد"},
        {"id": "C", "title_en": "Student Identity & Identifiers", "title_ar": "هوية الطالب والمعرفات الرسمية"},
        {"id": "D", "title_en": "Academic Records & Grading", "title_ar": "السجلات الأكاديمية ونظام العلامات"},
        {"id": "E", "title_en": "Curriculum & Plan Versioning", "title_ar": "الخطط الدراسية وإصداراتها"},
        {"id": "F", "title_en": "Courses & Offering Schedules", "title_ar": "المواد وجداول الشعب المطروحة"},
        {"id": "G", "title_en": "Registration & Seat Limits", "title_ar": "عمليات التسجيل والطاقة الاستيعابية"},
        {"id": "H", "title_en": "Webhooks & Real-Time Sync", "title_ar": "الإشعارات اللحظية والمزامنة"},
        {"id": "I", "title_en": "Rate Limits & Concurrency", "title_ar": "حدود الطلبات والتزامن"},
        {"id": "J", "title_en": "Network Architecture & Firewalls", "title_ar": "بنية الشبكة والجدران النارية"},
        {"id": "K", "title_en": "Single Sign-On (SSO)", "title_ar": "الدخول الموحد (SSO)"},
        {"id": "L", "title_en": "Sandbox Environment", "title_ar": "البيئة التجريبية للاختبار (Sandbox)"},
        {"id": "M", "title_en": "Technical Support & Escalation", "title_ar": "الدعم الفني ومصفوفة الطوارئ"},
    ]
}

# ---------------------------------------------------------------------------
# 4. Security Questionnaire Topics (Section 12)
# ---------------------------------------------------------------------------

SECURITY_QUESTIONNAIRE_SCHEMA = {
    "topics": [
        {"id": "SEC_TLS", "title_en": "Transport Layer Security (TLS 1.2+ / HTTPS)", "title_ar": "تشفير قنوات الاتصال"},
        {"id": "SEC_NET", "title_en": "Inbound / Outbound IP Allowlisting", "title_ar": "قوائم السماح لعناوين IP"},
        {"id": "SEC_AUTH", "title_en": "API Authentication & Scoped Access", "title_ar": "توثيق واجهات البرمجة وحصر الصلاحيات"},
        {"id": "SEC_TOKEN", "title_en": "Token Lifetime & Secret Rotation", "title_ar": "عمر الرموز وتدوير المفاتيح السرية"},
        {"id": "SEC_SSO", "title_en": "SSO Protocols & Signature Verification", "title_ar": "بروتوكول الدخول الموحد وتوقيع الرموز"},
        {"id": "SEC_WEBHOOK", "title_en": "Webhook HMAC-SHA256 Signatures & Replay Windows", "title_ar": "توقيع الويب هوك والحماية من هجمات الإعادة"},
        {"id": "SEC_RESIDENCY", "title_en": "Data Residency & Jurisdiction Standards", "title_ar": "مكان استضافة البيانات والامتثال المحلي"},
        {"id": "SEC_RETENTION", "title_en": "Data Retention & Minimization Policies", "title_ar": "سياسات تقليص واستبقاء البيانات"},
        {"id": "SEC_AUDIT", "title_en": "Audit Trails & Access Logging", "title_ar": "سجلات التدقيق وتتبع العمليات"},
        {"id": "SEC_ENV_SEP", "title_en": "Sandbox vs Production Isolation", "title_ar": "الفصل التام بين البيئة التجريبية والإنتاجية"},
        {"id": "SEC_INCIDENT", "title_en": "Incident Response & 24/7 Security Escalation", "title_ar": "الاستجابة للحوادث الأمنية"},
    ]
}

# ---------------------------------------------------------------------------
# 5. Data Requirements Matrix & Minimization (Sections 13 & 14)
# ---------------------------------------------------------------------------

DATA_REQUIREMENTS_MATRIX = {
    "entities": {
        "STUDENT": {
            "required": ["external_student_id", "full_name", "academic_program_code", "study_plan_number"],
            "conditionally_required": ["cumulative_gpa", "earned_credit_hours", "academic_standing"],
            "optional": ["email", "admission_year", "faculty_code"],
            "not_needed_strictly_excluded": [
                "financial_balance",
                "tuition_payment_status",
                "national_identification_number",
                "passport_number",
                "health_medical_records",
                "disciplinary_infractions",
                "housing_address",
                "guardian_information",
            ],
        },
        "COURSE": {
            "required": ["external_course_code", "title_ar", "credit_hours"],
            "conditionally_required": ["prerequisite_course_codes"],
            "optional": ["title_en", "course_level", "department_code"],
            "not_needed_strictly_excluded": ["course_fees", "budget_code"],
        },
        "GRADE_ATTEMPT": {
            "required": ["student_id", "course_code", "term_code", "outcome_passed_or_failed"],
            "conditionally_required": ["numeric_grade", "letter_grade", "attempt_sequence"],
            "optional": ["points", "quality_points"],
            "not_needed_strictly_excluded": ["instructor_personal_evaluations"],
        },
        "ENROLLMENT": {
            "required": ["student_id", "course_code", "term_code", "status"],
            "conditionally_required": ["section_code"],
            "optional": ["credits", "instructor_name"],
            "not_needed_strictly_excluded": ["payment_receipt_id"],
        },
        "STUDY_PLAN": {
            "required": ["plan_number", "faculty_code", "major_code", "total_required_credits", "required_courses"],
            "conditionally_required": ["requirement_groups", "minimum_pass_grade"],
            "optional": ["plan_title_ar", "admission_start_term"],
            "not_needed_strictly_excluded": ["accreditation_dossier_text"],
        },
        "OFFERING": {
            "required": ["section_id", "course_code", "term_code", "capacity", "enrolled", "available"],
            "conditionally_required": ["status"],
            "optional": ["meeting_schedule", "room", "instructor_name"],
            "not_needed_strictly_excluded": ["room_security_codes"],
        },
    }
}
