# Inbound Webhook Specification & Event Contract
# مواصفة أحداث الويب الفورية وإشعارات التكامل (Inbound Webhooks)

This document specifies the inbound webhook architecture that allows partner university Student Information Systems to push real-time event notifications to Morshidi.

---

## 1. Webhook Endpoint Specification
## رابط استقبال الأحداث الموحد

- **Receiver URL**:  
  `POST https://morshidi.onrender.com/api/v1/integrations/{tenant_key}/webhooks/{provider}`
  *(where `{tenant_key}` is the university identifier, e.g. `zarqa`, and `{provider}` is the integration adapter name, e.g. `generic_rest` or `fake_university`).*
- **Content-Type**: `application/json; charset=utf-8`
- **Method**: `POST`

---

## 2. Cryptographic Signature & Anti-Replay Defense
## التحقق من التوقيع الرقمي والحماية من إعادة الإرسال

To guarantee authenticity and protect against replay attacks, every incoming webhook must include two mandatory HTTP headers:

```http
X-Morshidi-Signature: sha256=d3b07384d113edec49eaa6238ad5ff00...
X-Morshidi-Timestamp: 1729422000
X-Event-Id: evt_9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d
```

### 2.1 HMAC-SHA256 Signature Calculation
The signature is computed over the raw UTF-8 request body using the shared Webhook Secret (`HMAC-SHA256`):
$$\text{Signature} = \text{HMAC-SHA256}(\text{key} = \text{WebhookSecret}, \text{message} = \text{raw\_body})$$

- Format in header: `sha256=<hex_digest>`
- Morshidi validates the signature using **constant-time byte comparison** (`hmac.compare_digest`) to prevent timing attacks.

### 2.2 Replay Protection Window (300 Seconds)
- The `X-Morshidi-Timestamp` represents the UNIX epoch timestamp (in seconds) of event generation.
- Morshidi compares the header timestamp against current UTC time:
  $$\Delta t = |t_{\text{current}} - t_{\text{header}}|$$
- If $\Delta t > 300\text{ seconds}$ (5 minutes), the webhook is **deterministically rejected** with HTTP 409 (`WEBHOOK_REPLAY_EXPIRED`).

### 2.3 Event Deduplication
- Morshidi records the `event_id` in a transient deduplication cache.
- Duplicate events with the same `event_id` receive an idempotent `200 OK` response without triggering duplicate processing.

---

## 3. Supported Event Types & Payload Schemas

### 3.1 Course Grade Posted (`student.grade_posted`)
Triggered when an instructor or registrar posts an official course grade.
- **Payload**:
```json
{
  "event_id": "evt_grade_001",
  "event_type": "student.grade_posted",
  "timestamp": "2026-10-20T10:15:00Z",
  "tenant_key": "zarqa",
  "data": {
    "student_id": "209900001",
    "course_code": "0301101",
    "term_code": "2026-1",
    "grade_code": "A",
    "numeric_grade": 91.5,
    "scale": 100,
    "passed": true,
    "credits": 3
  }
}
```
- **Morshidi Action**: Invalidates the student's prerequisite cache and recalculates graduation audit and degree path.

---

### 3.2 Enrollment Changed (`student.enrollment_changed`)
Triggered when a student adds, drops, or is administratively moved into a section.
- **Payload**:
```json
{
  "event_id": "evt_enroll_002",
  "event_type": "student.enrollment_changed",
  "timestamp": "2026-10-20T10:16:00Z",
  "tenant_key": "zarqa",
  "data": {
    "student_id": "209900001",
    "term_code": "2026-1",
    "course_code": "0301201",
    "section_id": "SEC-01",
    "action": "REGISTERED",
    "credits": 3
  }
}
```
- **Morshidi Action**: Updates current active credit load and schedule conflict matrix.

---

### 3.3 Section Capacity Changed (`offering.capacity_changed`)
Triggered when a section seat limit is adjusted or available seats reach 0.
- **Payload**:
```json
{
  "event_id": "evt_cap_003",
  "event_type": "offering.capacity_changed",
  "timestamp": "2026-10-20T10:17:00Z",
  "tenant_key": "zarqa",
  "data": {
    "term_code": "2026-1",
    "course_code": "0301201",
    "section_id": "SEC-01",
    "capacity": 35,
    "enrolled": 30,
    "available_seats": 5,
    "status": "OPEN"
  }
}
```
- **Morshidi Action**: Refreshes capacity intelligence metrics and institutional bottleneck alerts.

---

### 3.4 Curriculum Plan Updated (`curriculum.updated`)
Triggered when a study plan or prerequisite rule is officially modified.
- **Payload**:
```json
{
  "event_id": "evt_curric_004",
  "event_type": "curriculum.updated",
  "timestamp": "2026-10-20T10:18:00Z",
  "tenant_key": "zarqa",
  "data": {
    "plan_id": "ZU:IT:CS:P12",
    "faculty_code": "IT",
    "major_code": "CS",
    "modified_courses": ["0301201"]
  }
}
```
- **Morshidi Action**: Triggers an incremental catalog synchronization job for the affected major.

---

## 4. Expected Responses

- **Success (`200 OK`)**:
```json
{
  "received": true,
  "event_id": "evt_grade_001",
  "status": "PROCESSED",
  "timestamp": "2026-10-20T10:15:01Z"
}
```
- **Invalid Signature (`401 Unauthorized`)**:
```json
{
  "error": "WEBHOOK_SIGNATURE_INVALID",
  "message": "HMAC-SHA256 signature verification failed."
}
```
- **Replay Expired (`409 Conflict`)**:
```json
{
  "error": "WEBHOOK_TIMESTAMP_EXPIRED",
  "message": "Webhook timestamp exceeds 300-second maximum skew window."
}
```

