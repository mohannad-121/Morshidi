# Plan 12 source closure backlog

## Scope and current count

This is the authoritative Phase P1 source-resolution backlog for Zarqa University Artificial Intelligence Plan 12. It preserves uncertainty rather than resolving it by inference. The target-course source status count is **32 `verified`, 30 `not_applicable`, 4 `unresolved`, and 2 `source_conflict`** (68 Plan 12 memberships total). `verified` means structured prerequisite logic is present; `not_applicable` means no prerequisite is modeled. Neither count authorizes a claim about an unrecorded institutional source version.

For every non-verified target, current Phase 5 behavior is `REVIEW_REQUIRED`: the evaluator does not parse raw source text, structured dependency groups are absent, recommendations exclude the course from ranked results and place it in review-required results, and planners retain the review boundary. This behavior is intentional and tested.

Known catalog source: the Plan 12 seed registers one `official_study_plan` at `https://www.zu.edu.jo/ar/Collage/Science_and_Technology/Dept_Artificial/GetStudyPlan.aspx?Dept=1505&fac=15&id=110&page=205`, title “جامعة الزرقاء - قسم الذكاء الاصطناعي - الخطة الدراسية رقم (12)”. Its current `source_status` is `unknown`; no retrieved date, snapshot hash, effective date, or separate conflicting document is stored. “Known source” below therefore means the seeded source record and raw snapshot only, not independent verification.

## Non-verified Plan 12 target courses

| Course code | Canonical identity | Current status | Exact raw prerequisite/source text | Known source(s) | Issue | Current engine behavior | Official evidence needed | Closure owner/source | Closure status |
|---|---|---|---|---|---|---|---|---|---|
| `0200105` | مهارات الاتصال والتواصل (اللغة العربية 1), 3 credits, university required | `unresolved` | `0200150,0201001` | Seeded Plan 12 source; referenced-only codes `0200150`, `0201001` | The comma-delimited text does not establish operator semantics or identities/requirements for both referenced codes. | `REVIEW_REQUIRED`; no dependency group/options are executed. | Dated Plan 12/catalog or written academic ruling identifying both courses and exact AND/OR/other prerequisite semantics. | Zarqa curriculum authority / registrar; official plan or catalog version. | OPEN — `OFFICIAL_SOURCE_REQUIRED` |
| `0200106` | مهارات الاتصال والتواصل (اللغة الانجليزية 1), 3 credits, university required | `unresolved` | `0200151,0202001` | Seeded Plan 12 source; referenced-only codes `0200151`, `0202001` | The comma-delimited text does not establish operator semantics or identities/requirements for both referenced codes. | `REVIEW_REQUIRED`; no dependency group/options are executed. | Dated Plan 12/catalog or written academic ruling identifying both courses and exact AND/OR/other prerequisite semantics. | Zarqa curriculum authority / registrar; official plan or catalog version. | OPEN — `OFFICIAL_SOURCE_REQUIRED` |
| `1505311` | تعلم الالة, 3 credits, major required | `unresolved` | `1505101,1505201` | Seeded Plan 12 source. | The raw comma list has no authoritative conjunction/disjunction semantics in the stored source. | `REVIEW_REQUIRED`; no dependency group/options are executed. | Written, versioned prerequisite ruling that states whether both or one course is required and any minimum-grade condition. | Zarqa AI department / curriculum authority; official plan or catalog version. | OPEN — `OFFICIAL_SOURCE_REQUIRED` |
| `1505320` | تعلم الآلة المتقدم, 3 credits, major required | `source_conflict` | `0300103,1505311` | Seeded Plan 12 source; `0300103` is referenced-only. No separate conflicting artifact is stored in the repository. | Stored status records a source conflict; the repository does not retain the competing source text or resolution. | `REVIEW_REQUIRED`; no dependency group/options are executed. | Both source artifacts (or a superseding dated official decision) and exact prerequisite semantics, including the identity/status of `0300103`. | Zarqa curriculum authority / registrar; official plan/catalog and conflict-resolution record. | OPEN — `SOURCE_CONFLICT` |
| `1505366` | معالجة الصور الرقمية, 3 credits, major required | `source_conflict` | `0301241,1505101` | Seeded Plan 12 source; `0301241` is referenced-only. No separate conflicting artifact is stored in the repository. | Stored status records a source conflict; the repository does not retain the competing source text or resolution. | `REVIEW_REQUIRED`; no dependency group/options are executed. | Both source artifacts (or a superseding dated official decision) and exact prerequisite semantics, including the identity/status of `0301241`. | Zarqa curriculum authority / registrar; official plan/catalog and conflict-resolution record. | OPEN — `SOURCE_CONFLICT` |
| `1505461` | الرؤية الحاسوبية, 3 credits, major required | `unresolved` | `1505366,1505415` | Seeded Plan 12 source. | The raw comma list has no authoritative conjunction/disjunction semantics; one listed prerequisite itself has `source_conflict`. | `REVIEW_REQUIRED`; no dependency group/options are executed. | Written, versioned rule covering exact operator semantics and the resolved authoritative rule for `1505366`. | Zarqa AI department / curriculum authority; official plan or catalog version. | OPEN — `OFFICIAL_SOURCE_REQUIRED` |

All six rows block completion of the source-closure portions of **PROP-037** and **PROP-040**. They also preserve the limitations noted in **PROP-003** and gate later grade/performance-driven proposal claims only indirectly; no current rule is guessed.

## Referenced-only course audit

These are course identities created by `20260916231030_model_ai_plan12_prerequisites.sql` solely so a structured prerequisite option can refer to a known code. Each has `catalog_status = referenced_only`, null Arabic/English name, null credit hours (because it has no `study_plan_courses` membership), and is not a Plan 12 requirement. “Identity verified” below means only the code is recorded, not that an official course identity has been confirmed.

| Code | Referenced by Plan 12 raw source text | Official identity verified? | Credit hours known? | Plan 12 membership? | Current role | Additional evidence needed |
|---|---|---|---|---|---|---|
| `0200150` | `0200105`: `0200150,0201001` | No — code only | No | No | prerequisite-only placeholder | Official catalog identity, credit value if relevant, and rule semantics for `0200105` |
| `0200151` | `0200106`: `0200151,0202001` | No — code only | No | No | prerequisite-only placeholder | Official catalog identity, credit value if relevant, and rule semantics for `0200106` |
| `0201001` | `0200105`: `0200150,0201001` | No — code only | No | No | prerequisite-only placeholder | Official catalog identity, credit value if relevant, and rule semantics for `0200105` |
| `0202001` | `0200106`: `0200151,0202001` | No — code only | No | No | prerequisite-only placeholder | Official catalog identity, credit value if relevant, and rule semantics for `0200106` |
| `0300103` | `1505320`: `0300103,1505311` | No — code only | No | No | prerequisite-only placeholder | Official identity plus the competing/superseding source that closes the `1505320` conflict |
| `0301241` | `1505366`: `0301241,1505101` | No — code only | No | No | prerequisite-only placeholder | Official identity plus the competing/superseding source that closes the `1505366` conflict |

## Closure protocol

1. Obtain a dated, issuing-authority-authenticated source or written academic ruling for each backlog row.
2. Record the issuing authority, source URL/file identifier, source/effective version, retrieval/snapshot evidence, scope, extraction notes, and any competing source relation.
3. Have the designated curriculum authority approve exact prerequisite grouping semantics and any minimum-grade condition.
4. Only then update `academic_sources`, the target source link, `course_dependency_groups/options`, and `prerequisite_logic_status`; retain a source-version transition record.
5. Replay the catalog and run all-course trace, eligibility, recommendation, and degree-path regressions. A row cannot move from open status merely because its raw text appears parsable.

Until that protocol is complete, `REVIEW_REQUIRED` is the required safe behavior.
