# Morshidi Real University Pilot & SIS Integration Guide
# دليل الربط التقني لأنظمة معلومات الطلبة (SIS) وإطلاق المرحلة التجريبية

Welcome to the **Morshidi University Integration Documentation Suite**.
This documentation provides the technical specifications, architectural boundaries, security requirements, and verification protocols required for higher education institutions (Universities and Colleges) to integrate their Student Information Systems (SIS) with Morshidi.

---

## 1. Core Architectural & Governance Principles
## المبادئ الحاكمة للتكامل والأنظمة

### Principle 1: AI Explains — Deterministic Rules Decide
> **الذكاء الاصطناعي يشرح — والقواعد المحددة الصارمة تقرر**

- Academic eligibility, prerequisite satisfaction, degree progress, graduation clearance, registration conflict detection, and enrollment limits are **always determined by deterministic code engines and university policy**.
- Generative AI and LLMs in Morshidi **only explain, summarize, translate, and guide** based on governed evidence.
- LLMs are strictly forbidden from independently determining student eligibility or altering academic status.

### Principle 2: The University SIS Remains Authoritative
> **نظام الجامعة (SIS) يبقى المرجع الرسمي المعتمد دائماً**

- Morshidi **never** becomes the authoritative system of record for official student identity, official transcripts, official grades, official section capacities, or degree conferral.
- Morshidi consumes, validates, projects, simulates, explains, and submits permitted student actions through formal integration boundaries.
- Any change to student state (e.g. course registration or drop) is **only finalized once confirmed by the university SIS**.
- Morshidi maintains a read-only synchronized shadow state with continuous drift detection (Reconciliation).

### Principle 3: Zero Direct Database Access (Zero DB-to-DB)
> **حظر الاتصال المباشر بقواعد البيانات نهائياً**

- Morshidi **never** requests or requires direct SQL database connection (e.g., direct PostgreSQL, Oracle, or SQL Server connection) to the university SIS database.
- All integration occurs strictly via **HTTPS REST APIs**, **Signed Inbound Webhooks**, or **Enterprise SSO (OIDC/SAML)**.

### Principle 4: Strict Multi-Tenant Isolation
> **عزل صارم للبيانات بين الجامعات والمؤسسات التعليمية**

- Every university is modeled as an independent tenant (`tenant_key`) with isolated integration configs, entity mappings, sync jobs, reconciliation tables, and audit logs.
- Cross-tenant data access is physically prevented by database Foreign Keys and Row Level Security (RLS). Cross-tenant data leakage is **0**.

---

## 2. Integration Modes: Read-Only vs. Write-Enabled Pilot
## أنماط الإطلاق التجريبي

Morshidi supports two pilot operational modes:

| Pilot Mode | Mode Key | Capabilities Enabled | SIS Impact |
| :--- | :--- | :--- | :--- |
| **Read-Only Pilot** *(Default)* | `READ_ONLY_PILOT` | Identity auth, academic record read, degree audit, smart planner, what-if simulation, institutional analytics, copilot. | **Zero mutations.** Morshidi is completely non-mutating to SIS state. |
| **Write-Enabled Pilot** | `WRITE_ENABLED_PILOT` | All Read-Only capabilities **plus** authoritative registration preview, registration submission, and course drop. | Section seats and enrollments update atomically via the SIS API. |

A university typically begins with a **Read-Only Pilot** during initial evaluation and moves to **Write-Enabled Pilot** only after passing all 16 criteria of the Pilot Readiness Scorecard.

---

## 3. Documentation Suite Index
## فهرس وثائق الربط التقني

The documentation suite contains the following dedicated guides for University IT, Registrar, and Information Security teams:

1. [**SIS Integration Contract (API Spec)**](file:///d:/imporant/Morshidi-review/docs/pilot/sis-integration-contract.md)
   - Standard REST endpoints, HTTP methods, headers, JSON request/response envelopes, status codes, and capability negotiation.
2. [**Identity & SSO Requirements**](file:///d:/imporant/Morshidi-review/docs/pilot/identity-sso-requirements.md)
   - Authentication protocols (OIDC, SAML 2.0, Token Exchange), required claims (`sub`, `student_id`, `email`), user provisioning, and fail-closed identity conflict prevention.
3. [**Data Fields & Privacy Requirements**](file:///d:/imporant/Morshidi-review/docs/pilot/data-fields-required.md)
   - Field-by-field schema for Students, Curricula, Courses, Grades, Enrollments, Offerings, and Schedules. Data minimization standards and PII protection.
4. [**Network & Security Requirements**](file:///d:/imporant/Morshidi-review/docs/pilot/network-security-requirements.md)
   - TLS 1.3 / HTTPS encryption, IP allowlisting, strict SSRF defenses (RFC 1918, link-local, cloud metadata blocking), secret rotation, rate limiting, and audit logging.
5. [**Inbound Webhooks Contract**](file:///d:/imporant/Morshidi-review/docs/pilot/webhook-contract.md)
   - Real-time event notifications (`grade_posted`, `enrollment_changed`, `capacity_changed`), HMAC-SHA256 signatures, replay window (300s), and idempotency.
6. [**Synchronization & Drift Reconciliation**](file:///d:/imporant/Morshidi-review/docs/pilot/sync-reconciliation.md)
   - Full vs. incremental sync flows, cursor-based pagination, error isolation, and non-destructive reconciliation reporting.
7. [**Pilot Readiness Checklist (16-Point Scorecard)**](file:///d:/imporant/Morshidi-review/docs/pilot/pilot-readiness-checklist.md)
   - The official 16 technical criteria evaluated deterministically by Morshidi before launching a pilot.
8. [**Sandbox Testing Guide**](file:///d:/imporant/Morshidi-review/docs/pilot/sandbox-testing-guide.md)
   - How to test integrations against the official Morshidi Reference Sandbox (Fake University) prior to real campus integration.

---

## 4. Integration Lifecycle Overview
## مراحل تنفيذ الربط والتشغيل

```
[ المرحلة 1: الاتفاق والتهيئة ]
  ├── 1. تعيين معرف المستأجر (Tenant Key) واسم الجامعة
  ├── 2. توفير إعدادات الاتصال (Base URL, Secret Key)
  └── 3. تحديد الصلاحيات المصرحة (Capability Negotiation)

[ المرحلة 2: مطابقة الكيانات الأكاديمية ]
  ├── 1. مطابقة رموز الكليات والأقسام
  ├── 2. مطابقة التخصصات والخطط الدراسية
  └── 3. مطابقة رموز المواد والمتطلبات السابقة

[ المرحلة 3: المزامنة التجريبية والتحقق ]
  ├── 1. إجراء مزامنة كاملة (Full Sync) للكتالوج والشعب
  ├── 2. فحص الاتصال وقراءة عينة بيانات طلابية تجريبية
  └── 3. تشغيل تقرير الفروقات (Reconciliation Report)

[ المرحلة 4: تدقيق بطاقة الجاهزية ]
  ├── تقييم المعايير الـ 16 آلياً (Pilot Readiness Scorecard)
  └── اعتماد التشغيل التجريبي (Pilot Launch Approval)
```

---

## 5. Contact & Support

For integration inquiries, security reviews, or technical support during sandbox setup:
- **Architecture & Integration Team**: `it-integrations@morshidi.edu`
- **Security & Privacy Office**: `security@morshidi.edu`
- **Reference Sandbox Endpoint**: `https://fake-university-aqdn.onrender.com`

