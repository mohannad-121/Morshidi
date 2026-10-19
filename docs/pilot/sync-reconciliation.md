# Synchronization & Drift Reconciliation Engine
# محرك مزامنة البيانات واكتشاف الفروقات الأكاديمية (Reconciliation)

This document describes the synchronization mechanics, cursor-based incremental sync, batch error isolation, and non-destructive reconciliation reporting implemented in Morshidi.

---

## 1. Dual Synchronization Modes
## نمطا المزامنة: الشاملة والتدريجية

Morshidi supports two distinct synchronization modes managed by the `SyncOrchestrator`:

| Dimension | Full Sync (`FULL_SYNC`) | Incremental Sync (`INCREMENTAL_SYNC`) |
| :--- | :--- | :--- |
| **Trigger** | Initial tenant onboarding, major term change, manual admin trigger. | Scheduled recurring cron (hourly/daily) or webhook event. |
| **Scope** | All faculties, majors, plans, active courses, current offerings, and student identities. | Only records changed since the last confirmed `cursor`. |
| **Bandwidth** | Moderate to High (batched paginated queries). | Extremely Low (transfers only delta changes). |
| **Duration** | 10 to 60 seconds (depending on catalog size). | Under 1 second. |

---

## 2. Cursor-Based Incremental Synchronization
## المزامنة التدريجية المعتمدة على المؤشرات (Cursors)

When `INCREMENTAL_SYNC` runs:
1. Morshidi fetches the last successful `cursor` from `university_sync_jobs` for the university.
2. Morshidi passes `cursor` to the University SIS:  
   `GET /sync/changes?cursor={cursor}&limit=500`
3. The SIS responds with a `ChangeBatch`:
```json
{
  "cursor": "cursor_1729425000_902",
  "has_more": false,
  "changes": [
    {
      "entity_type": "GRADE",
      "external_id": "ATTEMPT-9821",
      "action": "UPSERT",
      "data": { "student_id": "209900001", "course_code": "0301101", "grade": "A" }
    },
    {
      "entity_type": "OFFERING",
      "external_id": "SEC-01",
      "action": "UPDATE_CAPACITY",
      "data": { "enrolled": 25, "available_seats": 5 }
    }
  ]
}
```
4. Morshidi applies changes sequentially and stores the new cursor only after all changes in the batch succeed.

---

## 3. Error Isolation & Fault Tolerance
## عزل الأخطاء واستمرارية المزامنة

A single corrupt or unmapped record must **never** halt the synchronization of an entire university:

- **Row-Level Try/Catch**: Each record in a sync batch is processed within an isolated transaction.
- **Metrics Collected per Job**:
  - `records_processed`
  - `records_created`
  - `records_updated`
  - `records_skipped`
  - `records_failed`
- **Failure Logging**: Any rejected record is logged with its exact error reason (e.g., `MAPPING_MISSING`) into `university_sync_jobs.error_details` without aborting the remaining 99.9% of valid records.

---

## 4. The Non-Destructive Reconciliation Engine
## محرك كشف الفروقات غير التدميري

Because **The University SIS Remains Authoritative**, Morshidi never silently mutates or forces changes when differences arise between SIS data and Morshidi local records. Instead, the `ReconciliationEngine` executes a deterministic comparison pass and populates `university_reconciliation_items`.

### Reconciliation Item Statuses:

| Status Code | Severity | Description | Recommended Action |
| :--- | :--- | :--- | :--- |
| `IN_SYNC` | Normal | Local state and SIS state match 100% (cryptographic hash matches). | None. |
| `MISSING_LOCALLY` | Warning | Entity exists in the University SIS but is absent in Morshidi shadow store. | Trigger targeted incremental sync. |
| `STALE_LOCALLY` | Warning | Morshidi record has an older modification timestamp than SIS. | Invalidate local cache and refresh. |
| `VALUE_MISMATCH` | High | Specific field conflict (e.g. earned credit discrepancy or grade mismatch). | Registrar review required. |
| `IDENTITY_MISMATCH` | Critical | Student ID is bound to a different subject or national ID. | Fail closed; notify Security & Registrar. |
| `MAPPING_MISSING` | High | SIS references a course/major code not present in `university_mappings`. | Add missing mapping via Integrations dashboard. |

### Reconciliation Record Structure:
```json
{
  "id": "rec_1849204",
  "university_id": "10000000-0000-0000-0000-000000000001",
  "entity_type": "STUDENT",
  "external_identifier": "209900001",
  "status": "VALUE_MISMATCH",
  "details": {
    "field": "earned_credits",
    "sis_value": 67,
    "morshidi_value": 64,
    "difference_reason": "Term 2026-1 grades finalized in SIS before Morshidi sync"
  },
  "detected_at": "2026-10-20T10:20:00Z",
  "resolved_at": null
}
```

Institutional administrators view all detected reconciliation items in real-time under the **تقرير الفروقات (Reconciliation)** tab in the Institutional Dashboard.

