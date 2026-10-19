# Pilot Readiness Checklist & 16-Point Scorecard
# قائمة التدقيق الفني للإطلاق التجريبي (16 معياراً حاسماً)

Before any real university pilot launches, Morshidi evaluates the technical integration against a **16-Point Deterministic Scorecard** implemented in `apps/api/app/sis_integration/pilot_readiness.py`.

This evaluation runs in real-time and is visible to university administrators in the Institutional Portal under **بطاقة الجاهزية (Readiness Scorecard)**.

---

## 1. The 16 Evaluated Technical Criteria

| # | Criterion Key | Arabic Title | Requirement for PASS | Severity if Failed |
| :-: | :--- | :--- | :--- | :--- |
| **1** | `TENANT_CONFIG_EXISTS` | إعدادات المستأجر | Tenant exists in `universities`, status is `ACTIVE`, valid timezone & locale. | **CRITICAL** |
| **2** | `INTEGRATION_CONFIG_EXISTS` | إعدادات التكامل الفني | Entry exists in `university_integration_configs` with valid `base_url` and provider. | **CRITICAL** |
| **3** | `CONNECTIVITY_PROBE` | فحص الاتصال الحي | Gateway responds to `GET /health` with HTTP 200 and latency $< 2000\text{ ms}$. | **CRITICAL** |
| **4** | `CAPABILITIES_DECLARED` | الصلاحيات المصرحة | Minimum required capabilities (`IDENTITY_AUTH`, `STUDENT_PROFILE_READ`, `GRADES_READ`, `CURRICULUM_READ`) declared. | **CRITICAL** |
| **5** | `SECRETS_CONFIGURED` | تشفير المفاتيح والسرية | Service key or secret reference resolved and safely masked (fingerprinted). | **CRITICAL** |
| **6** | `COURSE_MAPPINGS_COVERAGE` | مطابقة رموز المواد | $\ge 95\%$ of active SIS course codes mapped to canonical Morshidi course IDs. | **HIGH** |
| **7** | `PLAN_MAPPINGS_COVERAGE` | مطابقة الخطط الدراسية | $100\%$ of active SIS study plan IDs mapped to canonical plan numbers. | **CRITICAL** |
| **8** | `FACULTY_MAPPINGS_COVERAGE`| مطابقة الكليات والأقسام | $100\%$ of SIS faculties and majors mapped to canonical academic codes. | **CRITICAL** |
| **9** | `STUDENT_IDENTITIES_SYNCED`| مزامنة هويات الطلبة | Initial student identities loaded with valid `link_status = 'ACTIVE'`. | **HIGH** |
| **10**| `ENROLLMENTS_INITIALIZED` | تهيئة التسجيل الحالي | Current semester enrollments present in shadow store. | **MEDIUM** |
| **11**| `OFFERINGS_INITIALIZED` | تهيئة الشعب والمقاعد | Active term course offerings present with non-null capacities and meeting times. | **HIGH** |
| **12**| `WEBHOOKS_HEALTHY` | جاهزية أحداث الويب | HMAC-SHA256 signature key active; at least 1 verified test webhook received. | **MEDIUM** |
| **13**| `RECONCILIATION_CLEAR` | خلو تقرير الفروقات | Zero unresolved `IDENTITY_MISMATCH` or critical grade discrepancies. | **CRITICAL** |
| **14**| `SSO_VERIFIED` | جاهزية الدخول الموحد | OIDC discovery metadata reachable or SAML ACS endpoint configured. | **MEDIUM** |
| **15**| `AUDIT_LOGGING_ACTIVE` | تفعيل سجل التدقيق | `university_integration_audit_log` actively recording integration events. | **HIGH** |
| **16**| `PILOT_MODE_VALIDATED` | اعتماد نمط الإطلاق | Validated for `READ_ONLY_PILOT` or `WRITE_ENABLED_PILOT` based on authorization. | **CRITICAL** |

---

## 2. Overall Scorecard Calculation & Gate Logic

The `PilotReadinessScorecard` evaluates the overall status deterministically:

```
IF any CRITICAL criterion == "FAIL":
    overall_status = "BLOCKED"
    summary = "الإطلاق محظور: توجد متطلبات حيوية غير مكتملة."
ELSE IF any HIGH or MEDIUM criterion == "WARNING":
    overall_status = "WARNING"
    summary = "جاهز جزئياً مع وجود ملاحظات تحذيرية ينصح باستكمالها."
ELSE:
    overall_status = "PASS"
    summary = "جميع المتطلبات الفنية للإطلاق التجريبي مكتملة ومطابقة للمعايير."
```

---

## 3. University Readiness Milestone Checklist

Use this checklist during joint integration workshops between the University IT team and Morshidi Engineering:

### Phase 1: Environment & Network Readiness
- [ ] Public HTTPS DNS record established for University SIS Gateway.
- [ ] TLS 1.3 certificate installed and validated (public CA).
- [ ] Morshidi egress IP ranges allowlisted on campus perimeter firewalls.
- [ ] Non-RFC 1918 public IP or secure cloud proxy verified (passes Morshidi SSRF filter).

### Phase 2: Credentials & Secrets
- [ ] Secure Service Key generated with high entropy ($\ge 256$ bits).
- [ ] Webhook HMAC Secret generated and shared securely via encrypted channel.
- [ ] Credentials configured in Morshidi environment vault (zero database plaintext).

### Phase 3: Academic Mapping Sign-Off
- [ ] Faculty code translation table verified by College Dean.
- [ ] Major and Study Plan code translation table verified by Registrar.
- [ ] Course code translation table verified against catalog ($\ge 95\%$ coverage).
- [ ] University grading scale confirmed (4.0 vs 100-point scale).

### Phase 4: Verification in Sandbox
- [ ] Full catalog synchronization completed successfully.
- [ ] Sample test student login and transcript retrieval verified.
- [ ] Course offerings and section meeting times verified in Schedule Planner.
- [ ] Test webhook delivered and signature verified.
- [ ] Reconciliation pass confirms 0 `IDENTITY_MISMATCH`.
- [ ] 16-point scorecard displays `PASS`.

