# Required Data Fields & Privacy Specifications
# مواصفة البيانات المطلوبة ومعايير حماية الخصوصية الأكاديمية

This document details the exact data schema required by Morshidi from the partner university SIS, categorized by academic entity. It also defines the strict data minimization and privacy governance rules enforced by the platform.

---

## 1. Privacy & Data Minimization Governance
## سياسة الحد الأدنى من البيانات وحماية الخصوصية

Morshidi strictly follows the principle of **Data Minimization** (Privacy by Design):

1. **Academic Scope Only**:  
   Morshidi collects only the data strictly necessary for academic degree audit, prerequisite tracking, semester schedule planning, and capacity intelligence.
2. **Strictly Prohibited Data (Never Requested / Never Stored)**:
   - ❌ Student financial records, bank accounts, tuition balances, or payment histories.
   - ❌ Medical, health, or disability records.
   - ❌ Disciplinary files, police records, or conduct sanctions.
   - ❌ Personal phone numbers, home physical addresses, or family details.
   - ❌ Social media profiles or biometric data.
3. **Zero PII Exposure in Institutional Analytics**:  
   All institutional analytics, bottleneck metrics, capacity reports, and Copilot answers operate strictly on **anonymized, aggregated counts**. Any cohort with fewer than 3 students is automatically suppressed (`SUPPRESSED`) to prevent re-identification.

---

## 2. Entity Schemas & Field Requirements

### 2.1 Student Profile (`NormalizedStudent`)
Represents the student's active identity and enrollment standing within the university.

| Field Name | Type | Mandatory? | Description & Constraints | Example |
| :--- | :--- | :--- | :--- | :--- |
| `student_id` | String | **Mandatory** | University registration number. Must preserve leading zeros. | `"209900001"` |
| `national_id` | String | Optional | National identity number or passport number. | `"9991234567"` |
| `full_name_ar` | String | **Mandatory** | Official full name in Arabic. | `"أحمد خالد محمد"` |
| `full_name_en` | String | Optional | Official full name in English. | `"Ahmad Khaled"` |
| `email` | String | **Mandatory** | Official university email. | `"ahmad@uni.edu.jo"` |
| `faculty_code` | String | **Mandatory** | Code of the student's faculty/college. | `"IT"` |
| `major_code` | String | **Mandatory** | Code of the student's major. | `"CS"` |
| `study_plan_id` | String | **Mandatory** | Identifier or year of the student's degree plan. | `"PLAN-CS-2023"` |
| `admission_term`| String | **Mandatory** | Semester of first admission. Format: `YYYY-T`. | `"2023-1"` |
| `academic_status`| Enum | **Mandatory** | `REGULAR`, `PROBATION`, `DISMISSED`, `GRADUATED`, `SUSPENDED`. | `"REGULAR"` |
| `gpa` | Float | **Mandatory** | Cumulative GPA on the university scale. | `3.42` |
| `earned_credits`| Integer | **Mandatory** | Total successfully completed credit hours. | `64` |
| `advisor_name` | String | Optional | Name of assigned faculty academic advisor. | `"د. سامر عبد الله"` |

---

### 2.2 Course Grade Attempts (`NormalizedGradeAttempt`)
Represents the historical transcript of courses completed, failed, or repeated.

| Field Name | Type | Mandatory? | Description & Constraints | Example |
| :--- | :--- | :--- | :--- | :--- |
| `course_code` | String | **Mandatory** | University course code. | `"0301101"` |
| `term_code` | String | **Mandatory** | Academic term of the attempt. Format: `YYYY-T`. | `"2023-1"` |
| `credits` | Integer | **Mandatory** | Credit hours awarded for the course. | `3` |
| `grade_code` | String | **Mandatory** | Letter grade or code: `A`, `B+`, `C`, `D`, `F`, `P`, `W`. | `"A"` |
| `numeric_grade`| Float | Optional | Numeric score achieved. | `92.0` |
| `scale` | Integer | **Mandatory** | Grading scale used (`4` for 4.0 scale, `100` for 100-point scale). | `100` |
| `status` | Enum | **Mandatory** | `COMPLETED`, `IN_PROGRESS`, `WITHDRAWN`, `EXEMPTED`. | `"COMPLETED"` |
| `passed` | Boolean | **Mandatory** | Deterministic pass flag based on university grading policy. | `true` |

---

### 2.3 Current Semester Enrollments (`NormalizedEnrollment`)
Active registrations in the current semester.

| Field Name | Type | Mandatory? | Description & Constraints | Example |
| :--- | :--- | :--- | :--- | :--- |
| `course_code` | String | **Mandatory** | Registered course code. | `"0301201"` |
| `section_id` | String | **Mandatory** | Unique section identifier. | `"SEC-01"` |
| `credits` | Integer | **Mandatory** | Registered credit hours. | `3` |
| `status` | Enum | **Mandatory** | `REGISTERED`, `WAITLISTED`, `DROPPED`. | `"REGISTERED"` |
| `schedule` | Object | **Mandatory** | Days, start time, end time, room, instructor. | See Section 2.5 |

---

### 2.4 Curriculum & Academic Plans (`NormalizedStudyPlan`)
The governing curriculum requirements for degree completion.

| Field Name | Type | Mandatory? | Description & Constraints | Example |
| :--- | :--- | :--- | :--- | :--- |
| `plan_id` | String | **Mandatory** | Unique plan key. | `"ZU:IT:CS:P12"` |
| `faculty_code` | String | **Mandatory** | Faculty code. | `"IT"` |
| `major_code` | String | **Mandatory** | Major code. | `"CS"` |
| `total_credits`| Integer | **Mandatory** | Total credits required for graduation. | `132` |
| `groups` | Array | **Mandatory** | Requirement categories and credit requirements. | See Below |
| `courses` | Array | **Mandatory** | Course codes, group mappings, prerequisites. | See Below |

#### Requirement Categories Recognized:
- `UNIVERSITY_REQUIRED`: University compulsory courses.
- `UNIVERSITY_ELECTIVE`: University electives.
- `FACULTY_REQUIRED`: Faculty/College compulsory courses.
- `FACULTY_ELECTIVE`: Faculty/College electives.
- `MAJOR_REQUIRED`: Major core compulsory courses.
- `MAJOR_ELECTIVE`: Major electives.
- `FREE_ELECTIVE`: Free general electives.

---

### 2.5 Course Offerings & Section Schedules (`NormalizedOffering`)
Term schedule and available section seats.

| Field Name | Type | Mandatory? | Description & Constraints | Example |
| :--- | :--- | :--- | :--- | :--- |
| `term_code` | String | **Mandatory** | Academic term code. | `"2026-1"` |
| `course_code` | String | **Mandatory** | Course code offered. | `"0301201"` |
| `section_id` | String | **Mandatory** | Unique identifier for section. | `"SEC-01"` |
| `section_number`| String | **Mandatory** | Human-readable section number. | `"1"` |
| `capacity` | Integer | **Mandatory** | Maximum student capacity. | `30` |
| `enrolled` | Integer | **Mandatory** | Number of currently registered students. | `24` |
| `available_seats`| Integer | **Mandatory** | Calculated as `capacity - enrolled`. | `6` |
| `meeting_blocks`| Array | **Mandatory** | Day & time blocks for lectures/labs. | See Below |

#### Meeting Block Structure:
```json
{
  "days": ["Sun", "Tue", "Thu"],
  "start_time": "09:30",
  "end_time": "10:30",
  "room": "IT-204",
  "instructor": "د. عمر إبراهيم"
}
```
- `days`: Array containing standard tokens: `Sun`, `Mon`, `Tue`, `Wed`, `Thu`, `Sat`.
- `start_time` & `end_time`: 24-hour time format `HH:MM`.

---

## 3. Data Freshness & Caching Invariants

| Entity | Caching Policy | Invalidation Trigger |
| :--- | :--- | :--- |
| **Curricula & Catalog** | Cached 24 hours | Webhook: `curriculum.updated` or manual catalog sync |
| **Course Offerings** | Cached 15 minutes | Webhook: `offering.capacity_changed` |
| **Student Transcripts** | Cached 1 hour | Webhook: `student.grade_posted` or student login |
| **Live Section Seats** | Real-time (0 cache on register/preview) | Always queried directly at mutation time |

