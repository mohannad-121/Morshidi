# Morshidi Phase 8 Release-Readiness Report

Date: 2026-10-24 (Asia/Amman)

Branch: `release/notifications-phase1-4d-20261021`

Starting and current HEAD: `b434aadbb8f5839334254728620121ff378d5a18`

Scope: isolated local validation only; no production write, hosted-project mutation, deployment, staging, commit, push, registration toggle, or webhook event was performed.

## Executive result

The two pending migrations, real Auth/RLS/Storage behavior, tenant and curriculum isolation, deterministic Nursing reconciliation, offerings workflow, and full regression suites were exercised locally. Critical migration and security blockers found during validation were corrected before the final runs.

**Verdict: `GO FOR RELEASE PREPARATION`.**

This is not authorization to deploy and is not a claim that production is already ready. Release preparation must include human review, backup/preflight, ordered migrations, durable object upload and verification, deployment, and post-deployment smoke checks. JUST Computer Science remains intentionally blocked from authoritative import until normalized official curriculum and policy evidence exists.

## 1. Isolated environment

- Docker Engine 29.8.0 and Supabase CLI 2.116.0 were used locally.
- The local stack provided PostgreSQL 17, GoTrue Auth, PostgREST, and the Supabase Storage API.
- Disposable PostgreSQL clone databases were used for independent/combined upgrade and concurrency checks and removed afterward.
- The final `supabase db reset --local` completed all 31 migrations and seed on 2026-10-24.
- Final clean local state: 8 learning-material rows, 8 authorization rows, 0 policy package/version/rule fixtures, private `learning-materials` bucket, and 0 bucket objects. This is the expected pre-object-migration state.

## 2. Migration validation

### `20261022135845_add_learning_material_authorization.sql`

- Fresh install and existing-schema upgrade: passed.
- Standalone disposable-clone result: 8 materials, 8 authorizations, private bucket.
- Corrected a reserved SQL alias and a PostgreSQL-incompatible regex bound discovered by real resets.
- RLS enabled; browser grants are narrow; trigger functions are not executable by browser roles.
- Bucket is private, 50 MiB limited, and MIME restricted. No client object policy permits direct downloads.
- Seeded metadata remains `local_private` until a verified object-copy step changes each row to durable private Storage.

### `20261022141020_add_versioned_graduation_policies.sql`

- Fresh install, standalone upgrade, and combined ordering: passed.
- Standalone disposable-clone result: 6 policy tables.
- `service_role` default `TRUNCATE`, `REFERENCES`, and `TRIGGER` privileges were revoked before explicit grants.
- Lifecycle is forward-only: draft -> validated -> approved -> retired.
- Approval requires a source, applicability, and rules.
- Approved/retired versions and governed child rows are immutable.
- Transaction advisory locking serializes publication; a real two-session test made the second transaction wait about 3.3 seconds and rejected the overlapping approved interval.

### Upgrade safety and rollback

- Separate and combined clones preserved 17 plans, 619 courses, 111 requirement groups, and 1,155 plan-course memberships.
- Forced-error tests rolled both migrations back atomically.
- Independent matrix: learning migration `8:8:private`; policy migration 6 tables; combined migration `8:8:6`.

## 3. Real RLS, Auth, and Storage results

The opt-in local integration suite used synthetic GoTrue users and the actual local APIs. It verified:

- all nine new application tables have RLS and the intended grants;
- anonymous material discovery/download is denied;
- an authorized AI student sees exactly 8 AI materials and receives a short-lived signed download;
- Nursing and unmapped students see no AI material and the server route returns 404;
- direct private-object access is denied;
- shared access requires an explicit valid authorization;
- identical course codes across tenants do not cross boundaries;
- a curriculum revision does not inherit content or policy;
- unknown tenant/plan mappings fail closed;
- unsafe object paths and traversal are rejected;
- all eight uploaded objects re-download with matching byte sizes and SHA-256 hashes;
- an expired signed link cannot be reused;
- objects remain downloadable after restarting the Storage container;
- browser roles cannot write graduation-policy state.

A real test exposed a signed-URL shape difference (`/object/...` versus `/storage/v1/...`); the repository now normalizes only those supported rooted forms and rejects unexpected URLs.

The former public chapter binaries and discovery code are removed, so the old `/chapters/...` paths are not build artifacts. The checked-in private files are only controlled migration sources, not the production durability layer. Durable private Storage was proven locally, but production release preparation must run the object migration and verify every object before changing metadata away from `local_private`.

## 4. Original 19 backend failures

| Baseline group | Count | Cause | Resolution |
|---|---:|---|---|
| Advisor generic prerequisite questions | 4 | Generic definitions were misrouted as specific-course lookups. | Restored the bounded general-academic explanation route; focused regression passed. |
| CORS/settings | 11 | Allowed-origin configuration existed incompletely and middleware was not wired from settings. | Added validated origins and middleware wiring; focused regression passed. |
| Local Supabase connectivity | 4 | Local stack was stopped, not an application regression. | Recovered the local stack; all four passed against it. |

The initial recovered-stack run was 2,412 passed, 15 failed, 106 skipped. After corrections and complete local configuration, the final backend run was **2,537 passed, 0 failed, 1 skipped, 6 warnings in 388.67 seconds**. The sole skip is the separately gated legacy Phase 4d notification test (`MORSHIDI_PHASE4D_LOCAL=1`), whose isolated validation is documented in the progress record; it does not cover either Phase 8 migration.

During consolidation, the full suite also exposed an optional conversation-store outage causing the privacy export to fail as a whole. The route now catches only the typed `ConversationUnavailable`, returns the owner-scoped local export, and explicitly marks conversations unavailable. Its full focused suite passed 24 tests.

## 5. Nursing 29-credit reconciliation

- Canonical Nursing Plan 12 totals 132 credits.
- Deterministic reconciliation now accounts for 129 credits and emits one explicit 3-credit `FREE_ELECTIVE_POLICY_REQUIRED` category.
- The historical 29-hour presentation was an opaque aggregate from the earlier planner: it mixed requirements that could be placed deterministically with the unresolved institutional-policy requirement. The revised category/provenance breakdown places the supported requirements instead of reporting them as an undifferentiated remainder.
- No course was invented for the free elective and no institutional free-elective policy was fabricated.
- Electives are not double-counted; allocation is capped by canonical remaining credits.
- Zero-credit requirements remain present and enforced rather than being dropped as arithmetic noise.
- The 3 credits remain deliberately unscheduled because selecting an approved free elective requires an authoritative institutional rule.
- Focused Nursing/free-elective/degree-path validation: 21 passed; the broader Degree Path regression: 160 passed.

## 6. Offerings and academic calendar

The student flow now loads a tenant-scoped period catalog and initial semester offerings without manual course-code entry. It selects a registration-open period when present and provides academic-year and semester selectors.

Acceptance coverage includes Arabic first-character/partial search, Arabic normalization, English names, course codes, canonical identity selection, keyboard navigation, past/future periods, tenant calendars, authorized visibility, complete zero-offering periods, incomplete snapshots, unavailable providers, stale snapshots, and planner overlay behavior. The exact verified-empty/search-empty Arabic messages are:

- `لا يوجد مواد لهذا الفصل`
- `لا توجد مواد مطابقة لبحثك`

Incomplete, unavailable, and stale states never claim that no course is offered. Controls have keyboard focus behavior and mobile-sized touch targets. Results: backend offerings **36 passed**; frontend offerings **10 passed**; the complete frontend suite **259 passed**.

## 7. Multi-university isolation

Two fictional tenants were exercised transactionally with overlapping `CS101` codes but distinct identities, curricula, credit totals (12 and 3 in the bounded fixture), calendars, sections, chapter authorizations, graduation-project thresholds (9 and 3), policy packages/versions, and students. Cross-tenant writes were rejected by real RLS. A new curriculum revision inherited neither content nor policy. The transaction rolled back after assertions.

JUST Computer Science remains fail-closed and is not represented as authoritative data. `data/onboarding/just_cs_candidate.json` remains a blocked candidate pending official normalized sources and policy evidence.

## 8. Degree Path quality and benchmark

The local read-only benchmark ran twice per case and asserted identical semantic fingerprints across repeats while retaining distinct alternative paths.

| Case | End-to-end ms (runs) | Context ms | Engine ms | Validation ms | Peak working set | Outcome |
|---|---:|---:|---:|---:|---:|---|
| AI Plan 12 | 6,418 / 6,955 | 110 / 53 | 6,308 / 6,901 | 45 / 15 | 42.8 / 43.1 MiB | 2 distinct paths; policy review blocked |
| Nursing Plan 12 | 4,950 / 4,856 | 48 / 43 | 4,902 / 4,813 | 31 / 16 | 43.2 MiB | 2 distinct paths; free-elective policy blocked |
| Synthetic 180 credits / 60 required courses | 4,132 / 4,014 | 0.259 / 0.302 | 4,131.5 / 4,013.1 | 48 / 16 | 43.223 MiB | 2 distinct paths; modeled complete |

No performance improvement is claimed because there is no equivalent previous-release measurement. The measured results did not justify changing deterministic academic logic. No graduation dates or future offerings were fabricated.

## 9. Consolidated verification

| Check | Result |
|---|---|
| Final local Supabase reset | Passed, 31 migrations |
| Phase 8 real local integration | 4/4 passed in 23.14s |
| Full backend | 2,537 passed, 1 skipped, 6 warnings in 388.67s |
| API compilation | Passed |
| Full frontend Vitest | 43 files, 259 tests passed in 80.75s |
| TypeScript | Passed |
| Next.js production build | Passed; 41 pages generated |
| Focused offerings ESLint | Exit 0; 1 `set-state-in-effect` warning |
| Repository-wide ESLint | 2 errors, 63 warnings |
| `git diff --check` | Passed; line-ending notices only |

Principal commands (with environment values pointed only at loopback services and omitted here to avoid recording credentials):

- `supabase db reset --local`
- `apps/api/.venv311/Scripts/python.exe -m pytest -q`
- `apps/api/.venv311/Scripts/python.exe -m pytest apps/api/tests/test_phase8_local_supabase_integration.py -q`
- `apps/api/.venv311/Scripts/python.exe apps/api/scripts/benchmark_degree_path_phase8.py`
- `apps/api/.venv311/Scripts/python.exe -m compileall -q apps/api/app apps/api/scripts`
- `npm test -- --run`
- `npm run typecheck`
- `npm run lint`
- `npx eslint "src/app/(student)/student/offerings/page.tsx" "src/app/(student)/student/offerings/page.test.tsx" "src/lib/api/p10-offerings.ts"`
- `npm run build`

The two repository-wide ESLint errors are unescaped quotation marks at line 840 of unchanged `apps/web/src/app/institutional/pilots/[pilot_id]/page.tsx`. They pre-exist this dirty Phase 1-7/Phase 8 slice, do not affect compilation or the production build, and were classified rather than expanding scope into an unrelated institutional page. The 63 warnings are existing lint debt plus one warning in the offerings effect; there are no focused offerings lint errors.

## 10. Release ordering and rollback boundary

Human-controlled release preparation should use this order:

1. Review the complete dirty worktree and explicitly select only intended files; take database and object-storage backups and run read-only production preflight.
2. Apply `20261022135845_add_learning_material_authorization.sql`. This is backward compatible because rows remain `local_private` and no public object access is opened.
3. Apply `20261022141020_add_versioned_graduation_policies.sql`.
4. Deploy the backward-compatible API, including both existing single-course and new period-level offerings contracts.
5. Run `migrate_learning_materials_to_storage.py` in dry-run mode, then explicitly run the apply mode. It uploads and re-downloads every object, verifies size/hash, and only then changes that material's metadata. Retain source files until post-deployment acceptance.
6. Deploy the web client after the API endpoints are available.
7. Smoke-test authentication, owner/tenant resolution, AI authorized chapter access, Nursing denial, anonymous/direct-object denial, signed-link expiry, offerings states, privacy export, and deterministic Degree Path output.
8. Only after acceptance, schedule removal of migration-source binaries in a separate reviewed change. Never roll back by exposing the old public URLs.

The migrations are additive and preserve existing production identities, notification schemas/routes, academic catalog records, and current application contracts. The offerings API keeps the old course-specific route. No historical student record is rewritten.

## 11. Exact changed-file inventory

Pre-existing `.phase4d_isolated/` and `.phase4d_upgrade/` directories were preserved and are excluded from this Phase 1-8 inventory.

### API and domain

`apps/api/app/advisor/pre_router.py`; `apps/api/app/api/routes/learning_materials.py`; `apps/api/app/api/routes/offerings.py`; `apps/api/app/api/routes/privacy_p14.py`; `apps/api/app/api/schemas/degree_path.py`; `apps/api/app/core/config.py`; `apps/api/app/degree_path/engine.py`; `apps/api/app/degree_path/models.py`; `apps/api/app/degree_path/validation.py`; `apps/api/app/graduation_policy/__init__.py`; `apps/api/app/graduation_policy/catalog.py`; `apps/api/app/graduation_policy/models.py`; `apps/api/app/learning_materials/__init__.py`; `apps/api/app/learning_materials/models.py`; `apps/api/app/learning_materials/repository.py`; `apps/api/app/learning_materials/service.py`; `apps/api/app/main.py`; `apps/api/app/offerings/fake_provider.py`; `apps/api/app/offerings/models.py`; `apps/api/app/offerings/provider.py`; `apps/api/app/rules/project_credits.py`; `apps/api/app/university_onboarding/__init__.py`; `apps/api/app/university_onboarding/engine.py`; `apps/api/app/university_onboarding/models.py`.

### Scripts, fixtures, and tests

`apps/api/scripts/benchmark_degree_path_phase8.py`; `apps/api/scripts/migrate_learning_materials_to_storage.py`; `apps/api/tests/p10_synthetic_fixture.py`; `apps/api/tests/test_decision_history_local_supabase.py`; `apps/api/tests/test_decision_trace_persistence_local_supabase.py`; `apps/api/tests/test_decision_trace_persistence_service_local_supabase.py`; `apps/api/tests/test_degree_path_local_supabase.py`; `apps/api/tests/test_free_elective.py`; `apps/api/tests/test_graduation_policy.py`; `apps/api/tests/test_institutional_analytics_local_supabase.py`; `apps/api/tests/test_institutional_policy_local_supabase.py`; `apps/api/tests/test_learning_materials.py`; `apps/api/tests/test_mock_registration_persistence_local_supabase.py`; `apps/api/tests/test_p10_offerings_api.py`; `apps/api/tests/test_p10_offerings_local_supabase.py`; `apps/api/tests/test_p14_privacy.py`; `apps/api/tests/test_phase8_local_supabase_integration.py`; `apps/api/tests/test_policy_answer_local_supabase.py`; `apps/api/tests/test_policy_lexical_search_local_supabase.py`; `apps/api/tests/test_policy_semantic_local_supabase.py`; `apps/api/tests/test_student_diagnostic_local_supabase.py`; `apps/api/tests/test_university_onboarding.py`.

### Private migration sources

Eight files under `apps/api/private/learning-materials/zu/ai-p12/`: three PowerPoint files for course `1501112` and five PDF files for course `1505311`.

### Web

Deleted: the ten former public chapter files/metadata under `apps/web/public/chapters/`, plus `apps/web/src/lib/chapters/discovery.ts` and `discovery.test.ts`.

Modified/added: `apps/web/src/app/(student)/student/chapters/ChaptersClient.tsx`; `chapters/page.tsx`; `chapters/page.test.tsx`; `degree-path/page.tsx`; `offerings/page.tsx`; `offerings/page.test.tsx`; `portal-pages.test.tsx`; `apps/web/src/lib/api/learning-materials.ts`; `p10-offerings.ts`; `student-api.ts`; `student-types.ts`.

### Data, migrations, and documentation

`data/onboarding/just_cs_candidate.json`; `supabase/migrations/20261022135845_add_learning_material_authorization.sql`; `supabase/migrations/20261022141020_add_versioned_graduation_policies.sql`; `docs/CODEX_PROGRESS.md`; `docs/PHASE8_RELEASE_READINESS.md`.

## 12. Remaining release-preparation items

- Resolve or formally waive the unrelated repository-wide lint errors and warning debt under the project's release policy.
- Review all uncommitted Phase 1-8 changes; no files are staged.
- Validate production configuration values, especially CORS origins and service credentials, without exposing them.
- Execute and evidence the durable object migration in the target environment before removing local migration sources.
- Keep JUST import blocked until authoritative evidence is supplied.
- Obtain separate human approval before every stage, commit, push, migration, deployment, or other production action.

No critical Phase 8 security, database-migration, or deterministic academic-rule validation remains unverified in the isolated environment. These results support release preparation, not an unattended production release.

## Release-preparation addendum — 2026-10-24

The subsequent controlled release review resolved the two ESLint errors without disabling rules, added scoped ignore rules for the eight private local sources and disposable Phase 4d environments, and hardened the object migration with bucket-restriction validation, optimistic metadata switching, and idempotent verification of already-migrated objects. Real local execution produced `verified=8 migrated=8 already_migrated=0`, then `verified=8 migrated=0 already_migrated=8` on rerun.

Local database lint identified an invalid body in the already-revoked legacy unscoped notification RPC. The current application exclusively uses `ingest_university_event_scoped`; forward migration `20261024083357_drop_legacy_unscoped_university_event_rpc.sql` removes only the dead unscoped RPC. A fresh 32-migration reset passed, database lint then had zero errors, and a transactionally rolled-back scoped ingest returned `applied=true` while the legacy function was absent. The exact gated production procedure is in `docs/UNIVERSITY_READY_RELEASE_PLAN.md`.
