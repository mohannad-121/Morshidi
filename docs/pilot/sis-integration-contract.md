# Morshidi SIS Integration Contract Specification
# مواصفة عقد الربط التقني لأنظمة معلومات الطلبة (MORSHIDI_SIS_CONTRACT_V1)

**Contract Identifier**: `MORSHIDI_SIS_CONTRACT_V1`  
**Current Version**: `1.0.0`  
**Supported Transports**: HTTPS REST (JSON over TLS 1.3)  
**Encoding**: UTF-8  

---

## 1. Overview & Architecture Boundary

Morshidi interacts with partner university Student Information Systems (SIS) exclusively through a standardized, capability-negotiated REST API contract. The university SIS may either:
1. Implement the native **Morshidi SIS API Contract** directly on its integration gateway; or
2. Expose its existing institutional endpoints mapped via Morshidi's **Generic REST Adapter** layer.

All requests sent from Morshidi carry standard authorization headers, trace identifiers, and student ownership claims.

---

## 2. Capability Negotiation
## نظام التفاوض على القدرات والصلاحيات

To adhere to the principle of least privilege, the integration config declares explicitly which capabilities are permitted for the tenant. Morshidi enforces capabilities fail-closed at runtime: any attempt to execute an ungranted capability results in a deterministic `CapabilityNotGrantedError`.

| Capability Key | Description | Category | Required For |
| :--- | :--- | :--- | :--- |
| `IDENTITY_AUTH` | Verify student credentials or integration tokens | Identity | Login / Student Session |
| `STUDENT_PROFILE_READ` | Retrieve student personal and basic academic state | Student | Profile / GPA Display |
| `GRADES_READ` | Retrieve completed and graded course attempt history | Academic | Prerequisite Audit, Degree Audit |
| `ENROLLMENTS_READ` | Retrieve current semester active enrollments | Academic | In-Progress Load, Conflicts |
| `CURRICULUM_READ` | Fetch faculties, majors, plans, and course requirements | Curriculum | Degree Path, Planner |
| `OFFERINGS_READ` | Fetch term course offerings, sections, meeting blocks | Operations | Schedule & Seat Intelligence |
| `SECTION_CAPACITY` | Fetch real-time section seat limits and availability | Operations | Capacity Gauging |
| `REGISTRATION_PREVIEW` | Non-mutating preview of proposed course registration | Registration | Pre-Flight Registration Check |
| `REGISTRATION_WRITE` | Atomic registration of student into course sections | Registration | Write-Enabled Course Registration |
| `DROP_WRITE` | Atomic drop of student from registered sections | Registration | Course Withdrawal |
| `INCREMENTAL_SYNC` | Delta changes retrieval via cursor / change-batch | Sync | High-Efficiency Background Sync |
| `WEBHOOKS` | Inbound push notification support for real-time events | Eventing | Real-Time State Invalidation |
| `SSO` | Enterprise Single Sign-On federation (OIDC / SAML) | Identity | Campus Portal Seamless Login |

---

## 3. Standard Request & Response Envelopes

### 3.1 Common Request Headers
All HTTP requests made by Morshidi to the University SIS include:
```http
Authorization: Bearer <CONFIGURED_SECRET_OR_SERVICE_KEY>
X-Tenant-Key: <TENANT_KEY>
X-Correlation-Id: <UUIDv4>
Accept: application/json; charset=utf-8
User-Agent: Morshidi-SIS-Connector/1.0 (+https://morshidi.edu)
```
For student-scoped operations (e.g. registration, student profile), Morshidi attaches:
```http
X-Student-Id: <EXTERNAL_STUDENT_ID>
X-Idempotency-Key: <UUIDv4>
```

### 3.2 Standard Error Response Shape
When the University SIS rejects a request, it should return a standard RFC 7807 problem details object or the canonical Morshidi error JSON:
```json
{
  "error": "SECTION_FULL",
  "code": 409,
  "message": "Section 1 for course 0301101 has no available seats remaining.",
  "details": {
    "course_code": "0301101",
    "section_id": "SEC-001",
    "capacity": 30,
    "enrolled": 30
  },
  "timestamp": "2026-10-20T10:00:00Z"
}
```

Standard error codes recognized by the Morshidi integration engine:
- `UNAUTHORIZED` (401): Missing or expired integration token.
- `FORBIDDEN` (403): Operation not permitted for this student or tenant.
- `NOT_FOUND` (404): Entity does not exist.
- `PREREQUISITE_NOT_MET` (409): Student lacks required prerequisite course.
- `SECTION_FULL` (409): Zero seats remaining in section.
- `SCHEDULE_CONFLICT` (409): Section meeting time overlaps with current enrollment.
- `REGISTRATION_CLOSED` (409): Term registration window is closed.
- `CREDIT_LIMIT_EXCEEDED` (409): Exceeds maximum semester credit hours.
- `RATE_LIMITED` (429): SIS rate limit reached.

---

## 4. University SIS API Endpoints

### 4.1 Health Check & Operational Liveness
`GET /health` or `GET /healthz`  
Used by Morshidi automated health monitor (every 5 minutes).
- **Response `200 OK`**:
```json
{
  "ok": true,
  "ready": true,
  "service": "SIS Integration Gateway",
  "version": "2.4.0",
  "cursor": 412089
}
```

---

### 4.2 Student Identity & Academic Profile
`GET /student/me`  
Requires `STUDENT_PROFILE_READ`.
- **Response `200 OK`**:
```json
{
  "student_id": "209900001",
  "national_id": "9991234567",
  "full_name_ar": "أحمد خالد محمد",
  "full_name_en": "Ahmad Khaled Mohammad",
  "email": "ahmad@uni.edu.jo",
  "faculty_code": "IT",
  "major_code": "CS",
  "study_plan_id": "PLAN-CS-2023",
  "admission_term": "2023-1",
  "academic_status": "REGULAR",
  "gpa": 3.42,
  "earned_credits": 64,
  "advisor_name": "د. سامر عبد الله"
}
```

---

### 4.3 Completed Courses & Grades
`GET /student/grades`  
Requires `GRADES_READ`.  
Returns all past course attempts, grades, terms, and earned credits.
- **Response `200 OK`**:
```json
{
  "student_id": "209900001",
  "attempts": [
    {
      "course_code": "0301101",
      "course_name_ar": "أساسيات البرمجة",
      "term_code": "2023-1",
      "credits": 3,
      "grade_code": "A",
      "numeric_grade": 92.0,
      "scale": 100,
      "status": "COMPLETED",
      "passed": true
    },
    {
      "course_code": "0301102",
      "course_name_ar": "برمجة كينونية",
      "term_code": "2023-2",
      "credits": 3,
      "grade_code": "B+",
      "numeric_grade": 86.5,
      "scale": 100,
      "status": "COMPLETED",
      "passed": true
    }
  ]
}
```

---

### 4.4 Current Enrollments
`GET /student/enrollments`  
Requires `ENROLLMENTS_READ`.
- **Response `200 OK`**:
```json
{
  "student_id": "209900001",
  "term_code": "2026-1",
  "enrollments": [
    {
      "course_code": "0301201",
      "course_name_ar": "هياكل البيانات",
      "section_id": "SEC-01",
      "credits": 3,
      "schedule": {
        "days": ["Sun", "Tue", "Thu"],
        "start_time": "09:30",
        "end_time": "10:30",
        "room": "IT-204",
        "instructor": "د. عمر إبراهيم"
      },
      "status": "REGISTERED"
    }
  ]
}
```

---

### 4.5 Academic Curriculum & Requirements
`GET /curriculum/plans/{plan_id}`  
Requires `CURRICULUM_READ`.
- **Response `200 OK`**:
```json
{
  "plan_id": "PLAN-CS-2023",
  "faculty_code": "IT",
  "major_code": "CS",
  "degree": "BACHELOR",
  "total_credits": 132,
  "groups": [
    {
      "group_id": "GRP-REQ-UNIV",
      "name_ar": "متطلبات جامعة إجبارية",
      "required_credits": 18
    },
    {
      "group_id": "GRP-REQ-MAJOR",
      "name_ar": "متطلبات تخصص إجبارية",
      "required_credits": 66
    }
  ],
  "courses": [
    {
      "course_code": "0301101",
      "name_ar": "أساسيات البرمجة",
      "credits": 3,
      "group_id": "GRP-REQ-MAJOR",
      "prerequisites": []
    },
    {
      "course_code": "0301201",
      "name_ar": "هياكل البيانات",
      "credits": 3,
      "group_id": "GRP-REQ-MAJOR",
      "prerequisites": [
        {
          "prerequisite_code": "0301102",
          "min_grade": "D"
        }
      ]
    }
  ]
}
```

---

### 4.6 Term Course Offerings & Sections
`GET /offerings?term_code={term_code}`  
Requires `OFFERINGS_READ`.
- **Response `200 OK`**:
```json
{
  "term_code": "2026-1",
  "offerings": [
    {
      "course_code": "0301201",
      "course_name_ar": "هياكل البيانات",
      "credits": 3,
      "sections": [
        {
          "section_id": "SEC-01",
          "section_number": "1",
          "capacity": 30,
          "enrolled": 24,
          "available_seats": 6,
          "status": "OPEN",
          "meeting_blocks": [
            {
              "days": ["Sun", "Tue", "Thu"],
              "start_time": "09:30",
              "end_time": "10:30",
              "room": "IT-204",
              "instructor": "د. عمر إبراهيم"
            }
          ]
        }
      ]
    }
  ]
}
```

---

### 4.7 Authoritative Registration Preview (Non-Mutating)
`POST /registration/preview`  
Requires `REGISTRATION_PREVIEW`.
- **Request Body**:
```json
{
  "student_id": "209900001",
  "term_code": "2026-1",
  "section_ids": ["SEC-01"]
}
```
- **Response `200 OK`**:
```json
{
  "eligible": true,
  "warnings": [],
  "errors": [],
  "resulting_credits": 15,
  "simulation_only": true,
  "authoritative_data_mutated": false
}
```

---

### 4.8 Authoritative Registration Commit
`POST /registration/register`  
Requires `REGISTRATION_WRITE`.  
Requires `X-Idempotency-Key` header.
- **Request Body**:
```json
{
  "student_id": "209900001",
  "term_code": "2026-1",
  "section_ids": ["SEC-01"]
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "registered_sections": ["SEC-01"],
  "total_registered_credits": 15,
  "confirmed_at": "2026-10-20T10:05:00Z",
  "transaction_id": "TX-892104"
}
```

---

### 4.9 Authoritative Course Drop
`POST /registration/drop`  
Requires `DROP_WRITE`.  
Requires `X-Idempotency-Key` header.
- **Request Body**:
```json
{
  "student_id": "209900001",
  "term_code": "2026-1",
  "section_ids": ["SEC-01"]
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "dropped_sections": ["SEC-01"],
  "total_registered_credits": 12,
  "confirmed_at": "2026-10-20T10:07:00Z"
}
```

