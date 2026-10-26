# Morshidi University-Ready Controlled Release Plan

Prepared: 2026-10-24 (Asia/Amman)

Release branch: `release/university-ready-20261024`

Baseline: `b434aadbb8f5839334254728620121ff378d5a18`

Repository: public GitHub repository `mohannad-121/Morshidi`

## Release status and authority boundary

This branch is prepared for a controlled production rollout. It does not authorize a push, merge, database or Storage mutation, Render/Vercel deployment, registration-state change, or webhook event. Each production-changing phase below has its own explicit approval gate.

The reviewed local commit manifest contains exactly 83 intended paths. It excludes the private sources and disposable environments.

Phase 8 evidence is in `docs/PHASE8_RELEASE_READINESS.md`. The complete backend result was 2,537 passed with no failures; the complete frontend result was 259 passed; real local Auth/RLS/Storage and migration validation passed.

## 1. Included changes

The release combines the locally validated Phase 1-8 work and the final release-preparation hardening:

- Replace public chapter discovery and public binary URLs with authenticated, owner/tenant/plan/course-scoped learning-material APIs.
- Add private learning-material metadata, authorization, RLS/grants, integrity evidence, and a private Supabase Storage bucket migration.
- Add versioned, tenant-scoped graduation-policy governance with lifecycle validation, publication serialization, overlap rejection, immutability, and audit records.
- Add deterministic Degree Path unplaced-credit categories and validated Nursing 129 + 3 = 132 reconciliation.
- Add tenant-scoped academic-period discovery and searchable semester offerings with Arabic normalization, canonical course identity, keyboard/mobile behavior, and truthful provider states.
- Add deterministic university-onboarding validation while keeping JUST Computer Science blocked on authoritative normalized sources.
- Repair generic Advisor explanation routing, explicit CORS configuration, optional conversation-export degradation, and local integration fixture tenant keys.
- Remove the old public chapter files and unauthenticated chapter discovery module.
- Add local-only object migration and Degree Path benchmark tools plus focused and real local Supabase regression coverage.
- Ignore the two disposable `.phase4d_*` environments and all files under `apps/api/private/learning-materials/`.
- Make the object migration dry-run-first, hosted-target gated, bucket-policy validating, concurrency-safe, crash-recoverable, and idempotent.
- Prevent localhost from being implicitly trusted by CORS when `APP_ENV=production`.
- Resolve the two repository-wide ESLint errors without disabling rules.
- Add `20261024083357_drop_legacy_unscoped_university_event_rpc.sql`, which drops only the already-revoked invalid legacy RPC; the application and supported webhook path use `ingest_university_event_scoped`.

The exact Phase 1-8 file inventory is recorded in `docs/PHASE8_RELEASE_READINESS.md`. The exact release commit manifest must be reviewed with `git diff --cached --name-status` before commit and must match the categories below:

- API/domain: Advisor, CORS/configuration, learning materials, graduation policy, Degree Path, offerings, privacy, project-credit rules, onboarding, and application wiring.
- Tests/scripts: all corresponding focused, regression, real-local-Supabase, object-migration, and benchmark files.
- Web: authenticated Chapters, Degree Path explanations, offerings, safe API types/clients, the minimal institutional ESLint correction, and deletion of public discovery/files.
- Database/data: the two Phase 8 migrations, the legacy-RPC removal migration, and the fail-closed JUST candidate manifest.
- Documentation/configuration: `.gitignore`, safe `.env.example` placeholders, Phase 8 report, this plan, and the progress record.

## 2. Explicit exclusions

The following are not part of the commit, GitHub repository, or ordinary deployment artifact:

- `.phase4d_isolated/`
- `.phase4d_upgrade/`
- all eight files under `apps/api/private/learning-materials/`
- `.env`, `.env.*` other than placeholder examples, secrets, credentials, local Supabase state, database dumps, caches, build output, and editor state
- any production-generated output or copied production student data

The eight local sources must remain on the authorized operator workstation until production acceptance and backup confirmation. They must not be copied into a Render/Vercel build context.

## 3. Private chapter security and history limitation

The eight local files exist and match the migration metadata byte-for-byte and SHA-256-for-SHA-256. Git ignore rules cover the entire private source directory. None of the new private paths is tracked or staged.

The same binary contents were previously committed at `apps/web/public/chapters/` in historical commit `4a503ec`. This release deletes the live paths, but public Git history, forks, clones, caches, and prior deployment artifacts may retain the files. If the content is confidential or distribution rights require revocation, deletion in this commit is insufficient. The content owner must choose one or more separately approved actions:

1. rotate/replace the materials and treat historical copies as disclosed;
2. coordinate a `git filter-repo`/BFG history rewrite and force-push with all collaborators;
3. contact GitHub and affected hosting/CDN providers for cache or sensitive-data remediation; and
4. review forks and prior deployment artifacts.

No history rewrite is part of this plan. A rewrite is disruptive and cannot guarantee removal from existing clones or forks.

The application has no public Storage policy. Material metadata is owner/tenant/plan/course scoped before the server creates a signed URL. Signed URLs expire after at most 120 seconds. Auth-key rotation does not revoke an already-created Supabase Storage signed URL; emergency revocation requires deleting or replacing the object and considering CDN cache propagation.

The `local_private` server path remains a fail-closed migration bridge. It resolves beneath a fixed private root and verifies size/hash before an authenticated response. Because the source directory is ignored and excluded from the deployment artifact, production cannot silently depend on bundled files. Production availability begins only after the durable private-object migration succeeds.

## 4. Required production configuration

Validate presence and scope without printing values:

### Backend

- `APP_ENV=production`
- `FRONTEND_URL` — canonical production web origin
- `CORS_ALLOWED_ORIGINS` — comma-separated, explicit trusted preview origins only; no wildcard
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY` — server-only, never `NEXT_PUBLIC_*`
- `UNI_BASE_URL`
- `UNI_CLIENT_ID`
- `UNI_CLIENT_SECRET` when the upstream contract requires it
- `UNI_SERVICE_KEY` only when the legacy `X-Uni-Api-Key` compatibility path or institutional offering enrichment is intentionally enabled; it is not used by token-authenticated registration offerings
- `UNI_WEBHOOK_SECRET`
- `UNI_INTERNAL_AUTH_SECRET`
- `UNI_UNIVERSITY_ID`
- existing Advisor/policy embedding keys and model settings when those optional services are enabled

### Web

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`

Only the publishable Supabase key belongs in browser configuration. Production Render name presence was reconciled on 2026-10-25: every currently required/enabled-feature name is visible, while conditional `UNI_SERVICE_KEY` is absent; `APP_NAME` and `APP_VERSION` are additional valid metadata. Names do not attest values or effective runtime configuration. An authorized operator must still verify exact project/university IDs, origins, secret counterpart pairing, linked-group precedence, and that the active deployment received the saved configuration, without copying values into tickets, logs, or this repository.

### Offerings credential boundary

`UNI_CLIENT_ID` and `UNI_CLIENT_SECRET` authenticate student login/token exchange; registration offerings then use the short-lived student bearer token. The revised local release wiring uses that existing owner-scoped path for student period/course offerings. It validates the configured tenant, current academic term, initialized source manifest, explicit synthetic/institutional classification, canonical course codes, section identities, schedule facts, status/capacity consistency, and complete-empty semantics. Invalid, cross-tenant, uninitialized, or incomplete facts fail closed. No new secret or provider-selection variable is required.

The currently authorized university manifest identifies the source as synthetic. Those results must remain visibly `SYNTHETIC`; they are useful for end-to-end integration but are not real institutional evidence. A source may be labeled `INSTITUTIONAL` only when the same authorized manifest explicitly says `synthetic=false`. The existing course catalog remains responsible for Arabic/English course discovery and canonical identity; the adapter does not replace deterministic academic eligibility or planning rules.

`UNI_SERVICE_KEY` remains confined to the older `X-Uni-Api-Key` compatibility methods. The institutional analytics adapter calls those methods but safely degrades to incomplete offering enrichment when the key/source is unavailable.

If compatibility enrichment is required, the authorized university-integration operator must issue or rotate the shared credential under the university service's policy, store the same secret server-side on both services, and coordinate deployment in a separately approved change window. Never generate it ad hoc, expose it, or place it in browser configuration. It is not a prerequisite for the owner-scoped student offering adapter.

## 5. Backups and baseline capture

Approval gate A is required before any production read or backup operation.

1. Confirm the intended project reference, region, current deployed backend/frontend commit SHAs, migration-history head, PostgreSQL version, and maintenance window.
2. Confirm point-in-time recovery status and retention. Take a provider-supported logical/snapshot backup immediately before migration.
3. Export schema-only metadata and record row counts for academic catalog, identities, profiles, progress, notifications, learning-material tables if present, and policy tables if present.
4. Inventory the target Storage bucket configuration and object list. If objects already exist, preserve an object inventory with size, content type, checksum where available, and version/ETag.
5. Confirm recovery credentials and responsible operator before continuing. Do not place backup files in the repository workspace.

## 6. Production read-only preflight

Approval gate B is required before connecting to production. The preflight must be read-only.

- Verify production is at the expected baseline and no unknown migrations conflict with the three release migrations.
- Verify the canonical university, AI Plan 12, and course IDs referenced by the learning-material seed exist exactly once.
- Verify the two migrations' deterministic IDs do not collide with unrelated rows.
- Verify legacy academic counts and a sample of identity/profile/progress/notification counts against the backup record.
- Verify the scoped notification RPC exists and the legacy unscoped RPC is revoked before its removal.
- Verify the deployed backend already calls `ingest_university_event_scoped`.
- Verify target `APP_ENV`, frontend/CORS origins, Supabase project/server credential, university base/client/scope, and webhook/internal secrets are present, correctly paired, and active without revealing values.
- Review and make immutable the owner-scoped student offering adapter; accept visibly synthetic results for the current source or defer the feature until manifest-backed institutional data exists. Do not relabel synthetic data. Decide separately whether optional institutional analytics enrichment justifies a university-issued compatibility key.
- Confirm there is no active registration-state operation or webhook replay window overlapping the release.

Any mismatch stops the rollout. Do not edit production data to make a preflight pass.

## 7. Migration order

Approval gate C is required for database writes.

Apply one migration at a time in lexical order and inspect the result before proceeding:

1. `20261022135845_add_learning_material_authorization.sql`
2. `20261022141020_add_versioned_graduation_policies.sql`
3. `20261024083357_drop_legacy_unscoped_university_event_rpc.sql`

The first migration creates private metadata/authorization and keeps all eight rows at `local_private`; it does not write Supabase-owned Storage tables. The second adds empty governed policy structures and does not publish invented policy. The third drops only the already-revoked unscoped event RPC; the supported scoped RPC remains.

After each migration, verify migration history, transaction completion, grants, RLS, trigger-function execution privileges, counts, and unchanged legacy academic/identity/notification counts. Stop on any discrepancy. Do not manually mark a failed migration applied.

### Separate private-bucket provisioning gate

The `learning-materials` bucket is a separate Supabase Storage API operation after database migration acceptance and before object upload. It requires explicit Storage-write approval; Gate C database-migration approval does not authorize it.

Run a dry check first with server-only credentials on the secured operator workstation:

```powershell
apps/api/.venv311/Scripts/python.exe apps/api/scripts/provision_learning_material_bucket.py --allow-hosted
```

If absent, the expected result is `creation required`. After separate approval, add `--apply`. The operation is idempotent and fails closed if an existing bucket differs from the exact contract: private, 50 MiB, and the approved PDF/PowerPoint/Word MIME allowlist. It creates no browser object policy and re-reads the bucket after creation. Never place the server key in arguments, logs, Git, or browser configuration.

## 8. Backend deployment

Approval gate D is required to deploy.

Deploy the API before the web client. The API is backward-compatible with the currently deployed frontend: existing academic routes and the course-specific offerings route remain; the new period-level and learning-material routes are additive.

Before promotion, verify health, startup with server-only Supabase credentials, `APP_ENV=production`, explicit CORS origins, scoped notification RPC calls, and no private source directory in the deployment manifest. During the gap before object upload, learning-material downloads fail closed because production has no bundled local sources.

## 9. Private object upload

Run this only from the secured workstation that holds the ignored source files. Never run it in a public CI job and never copy the sources into Git.

Approval gate E permits a hosted dry run only:

```powershell
$env:SUPABASE_URL = '<production URL supplied securely>'
$env:SUPABASE_SERVICE_ROLE_KEY = '<server key supplied securely>'
apps/api/.venv311/Scripts/python.exe apps/api/scripts/migrate_learning_materials_to_storage.py --allow-hosted
```

Expected: `verified=8 migrated=0 already_migrated=0` before the first upload. The command verifies local path containment, local byte sizes/hashes, non-public bucket state, 50 MiB limit, and the exact approved PDF/PowerPoint/Word MIME restrictions. A dry run does not upload or patch metadata.

Approval gate F separately permits the write:

```powershell
apps/api/.venv311/Scripts/python.exe apps/api/scripts/migrate_learning_materials_to_storage.py --apply --allow-hosted
```

For each row, the tool uploads/upserts, downloads through authenticated private Storage, verifies size/SHA-256, and then conditionally switches metadata only if ID/provider/hash/size/path are unchanged. If interrupted, safely rerun it: already-migrated rows are re-downloaded and verified without writes; uploaded-but-not-switched rows are verified/uploaded again and then switched. The tool never makes the bucket public and never prints the key.

Expected first apply: `verified=8 migrated=8 already_migrated=0`. Expected immediate verification rerun: `verified=8 migrated=0 already_migrated=8`.

Afterward, independently verify exactly eight private objects, metadata provider/bucket state, sizes, hashes, MIME types, anonymous/direct denial, authorized AI signed download, Nursing denial, and expiry. Retain the workstation copies.

## 10. Frontend deployment

Approval gate G is required after backend and object acceptance.

Deploy the web commit. Verify the build uses only publishable browser values and the intended API origin. Confirm that no `public/chapters` files and no `apps/api/private` sources appear in either web or API artifacts.

## 11. Post-deployment acceptance

Approval gate H permits read-only/synthetic smoke tests but not real-student record mutation, registration toggles, or webhook events unless separately authorized.

- Authentication: sign-in/session refresh, owner mapping, cross-user denial.
- Chapters: AI list/download, Nursing/unmapped denial, old public URL 404, direct private object denial, signed-link expiry, hash/size integrity.
- Academic state: identity/profile/progress unchanged; Nursing remains 129 + 3 policy-required; no fake free-elective course.
- Degree Path: deterministic replay fingerprint and meaningful alternatives unchanged for approved synthetic/read-only fixtures.
- Offerings: tenant calendar, registration-open selection, Arabic/English/code search, complete-empty vs incomplete/unavailable/stale states.
- Notifications: read existing notifications and SSE reconnection/authorization. Do not send a production webhook under this plan.
- Advisor/privacy: generic prerequisite explanation, owner-scoped privacy export, explicit optional conversation-store outage state.
- CORS: production origin allowed, arbitrary and localhost origins rejected.
- Observability: no credential material, student data, signed URLs, or private payloads in logs.

## 12. Rollback and recovery

- Stop immediately on an authorization, isolation, integrity, or record-count discrepancy.
- Prefer application rollback and feature unavailability over weakening RLS or exposing Storage.
- The schema changes are additive. Do not hand-edit migration history or destructively down-migrate during an incident.
- If backend deployment fails, roll back the API artifact. Existing frontend contracts remain supported.
- If object upload fails before a metadata switch, the row stays `local_private`; retry from the secured workstation. An orphaned object remains private.
- If metadata switches but acceptance fails, disable the affected authorization/publication or roll back the API while preserving the private objects for investigation. Do not publish the bucket and do not restore old public paths.
- If object access must be revoked urgently, delete/replace the private object with separate approval and account for CDN propagation; rotating Auth keys alone does not revoke Storage signed URLs.
- Restore the database from the confirmed backup/PITR only through the provider's incident process and only after preserving failure evidence.
- The removed legacy RPC was already revoked and unsupported. Do not restore it to accommodate an obsolete backend; deploy the scoped backend.

## 13. Known risks

- Historical public Git exposure of the eight binaries cannot be reversed by this commit.
- Hosted environment-variable presence has not been verified locally.
- The production object migration is not executed or proven until gates E/F are approved.
- Three pre-existing PL/pgSQL lint warnings remain in unrelated earlier functions; local database lint has no errors.
- Frontend ESLint has 63 warnings but zero errors; no rule was disabled.
- JUST Computer Science remains intentionally blocked.
- Signed URLs remain usable until expiry and may be affected by CDN cache behavior.

## 14. Approval ledger

Each approval should identify environment, operator, timestamp, baseline SHA, backup evidence, and accepted result:

- A — backup/baseline capture
- B — production read-only preflight
- C — three database migrations
- D — backend deployment
- E — hosted object dry run
- F — private object upload and verification
- G — frontend deployment
- H — post-deployment smoke and final acceptance
- I — removal of local source copies, only after retention/legal requirements and successful acceptance

No gate is implied by approval of another gate.
