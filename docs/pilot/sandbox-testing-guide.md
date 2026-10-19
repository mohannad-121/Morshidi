# Sandbox Testing & Verification Guide
# دليل اختبار التكامل والتشغيل في البيئة التجريبية (Sandbox)

Before connecting any live university system or staging server, the partner university IT team can test and validate their integration designs against the **Official Morshidi Reference Sandbox (Fake University)**.

---

## 1. What is the Reference Sandbox?
## ما هي الجامعة التجريبية (Reference SIS Sandbox)؟

The Reference Sandbox is a fully functional, production-deployed Student Information System developed to the exact specifications of `MORSHIDI_SIS_CONTRACT_V1`.

- **Live Sandbox URL**: `https://fake-university-aqdn.onrender.com`
- **Source Code Repository**: `https://github.com/muayid-rabah/morshidi-uni` (Local path: `D:\imporant\morshidi-uni-review`)
- **Supported Academic Plans**: 17 complete degree curricula across 7 colleges (Computer Science, Artificial Intelligence, Software Engineering, Cybersecurity, Mathematics, Physics, Arabic, English, Translation, History, Economics, Business Administration, Accounting, Digital Journalism, Radio & TV, Law, Nursing).
- **Synthetic Data**: 23 synthetic student profiles with diverse academic standings (regular, near graduation, prerequisite-blocked, on academic warning).

---

## 2. Testing Capabilities in the Sandbox

University engineers can use the sandbox to observe and verify:

1. **Authentication & Token Exchange**:  
   Examine how short-lived integration tokens are issued and validated (`POST /api/integrations/morshidi/v1/student/registration/context`).
2. **Catalog & Plan Payloads**:  
   Inspect JSON formatting for requirement groups, courses, prerequisites, and credit allocations.
3. **Offerings & Section Meeting Blocks**:  
   Verify section schedules with multiple meeting times, lecture halls, and instructor assignments.
4. **Registration Preview & Non-Mutating Verification**:  
   Test simulated registration to verify that preview requests never decrement section seats.
5. **Atomic Final-Seat Registration**:  
   Test concurrent registrations for sections with only 1 remaining seat to observe atomic database locks and zero double-booking.
6. **Course Drop & Seat Restoration**:  
   Observe seat restoration upon drop and idempotency verification on retried requests.

---

## 3. Running Automated Contract Verification Tests

Morshidi includes an automated test kit that validates any target SIS against `MORSHIDI_SIS_CONTRACT_V1`:

### 3.1 Executing the SIS Contract Kit:
From the Morshidi repository root:
```bash
# Run the contract compliance suite
apps/api/.venv311/Scripts/python.exe -m pytest apps/api/tests/test_sis_contract_kit.py -v
```

This test suite verifies:
- `test_generic_rest_adapter_conforms_to_contract`: Confirms that the `GenericRestAdapter` correctly maps endpoints, parses normalized models, and respects timeout policies.
- `test_fake_university_adapter_conforms_to_contract`: Confirms that the `FakeUniversityAdapter` successfully interacts with the reference sandbox, translates grades, and handles schedules.

### 3.2 Executing Security & Multi-Tenant Isolation Tests:
```bash
# Run security, SSRF, and tenant isolation tests
apps/api/.venv311/Scripts/python.exe -m pytest apps/api/tests/test_sis_security_and_tenants.py apps/api/tests/test_sis_multi_tenant_isolation.py -v
```

This verifies:
- Complete isolation between Tenant A and Tenant B (`CROSS_TENANT_DATA_LEAKAGE = 0`).
- SSRF blocking of private IP ranges and cloud metadata endpoints.
- Secret masking in API responses.
- HMAC-SHA256 signature verification and 300s replay rejection.

---

## 4. Onboarding a New University in Sandbox Mode
## خطوات إضافة مستأجر جديد في نمط Sandbox

1. **Register the University Tenant**:
   ```sql
   INSERT INTO universities (id, name_ar, name_en, country, timezone, default_locale, status, active, tenant_key)
   VALUES ('20000000-0000-0000-0000-000000000002', 'جامعة اليرموك التجريبية', 'Yarmouk Pilot Sandbox', 'Jordan', 'Asia/Amman', 'ar', 'ACTIVE', true, 'yarmouk_sandbox');
   ```

2. **Configure the Integration Gateway**:
   ```sql
   INSERT INTO university_integration_configs (
     university_id, provider_type, base_url, auth_method, secret_env_ref, api_version,
     supported_capabilities, pilot_mode, timeouts_ms, rate_limit_rpm, active
   ) VALUES (
     '20000000-0000-0000-0000-000000000002',
     'generic_rest',
     'https://fake-university-aqdn.onrender.com',
     'token',
     'YARMOUK_SERVICE_KEY',
     'v1',
     ARRAY['IDENTITY_AUTH', 'STUDENT_PROFILE_READ', 'GRADES_READ', 'CURRICULUM_READ', 'OFFERINGS_READ', 'SECTION_CAPACITY', 'REGISTRATION_PREVIEW'],
     'READ_ONLY_PILOT',
     '{"connect": 5000, "read": 10000}',
     600,
     true
   );
   ```

3. **Verify Health in Institutional Portal**:
   - Navigate to `https://morshidi.vercel.app/institutional/integrations` (or `http://localhost:3000/institutional/integrations`).
   - Select `جامعة اليرموك التجريبية (yarmouk_sandbox)` from the university dropdown.
   - Verify health indicator is **متصل وسليم (HEALTHY)**.
   - Run the 16-point scorecard to review readiness.

