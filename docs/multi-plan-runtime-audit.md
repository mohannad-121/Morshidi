# Multi-Plan Runtime Audit

Date: 2026-10-17  
Scope: Fake University student integration, Morshidi synchronization, and deterministic academic engines  
Identity contract: `institution + faculty + major + plan number`, serialized as `planKey` (for example, `ZU:IT:AI:P12`)

This audit classifies every material Plan 12 or single-major dependency found during the Multi-Major / Multi-Plan Foundation slice. Plan number alone is never a curriculum identifier.

## A. Harmless fixture or demo assumptions

- The existing Fake University seed manifest and generated demo catalog contain the original AI Plan 12 dataset. They remain demo data, not a runtime lookup rule.
- Morshidi seed fixtures, taxonomy tests, and labels that explicitly name the AI Plan 12 remain valid fixtures for that curriculum.
- Numeric credit totals inside historical test inputs are retained when they describe a particular fixture. Portal and integration outputs no longer derive requirements from those literals.

## B. Runtime blockers fixed in this slice

- Fake University integration routes previously exposed the global course catalog. They now resolve the authenticated student's exact `planKey` and return only that curriculum's membership.
- Fake University academic-plan serialization previously hardcoded 132 credits. The total and requirement groups now come from the resolved curriculum.
- Fake University student records can now retain `planKey`, `planNumber`, `facultyCode`, and `majorCode`; legacy inference is restricted to the exact existing AI Plan 12 fixture.
- Morshidi previously resolved by plan number and could choose the first match. It now traverses the institution-scoped faculty/major/plan relation and requires exactly one matching composite identity.
- Unknown, malformed, inconsistent, or ambiguous curriculum identity now fails closed with typed synchronization errors.
- Existing Morshidi academic profiles now update `study_plan_id` after exact resolution instead of retaining a stale plan.
- Portal progress totals and requirement-group totals now come from student curriculum metadata.
- The portal's graduation-project rule previously matched course names. It is now limited to the exact AI plan and governed project course codes.

## C. Intentionally AI-specific logic retained

- Student Intelligence skill mappings and workload definitions are explicitly registered only for the AI Plan 12 curriculum. Other plans receive an unsupported-curriculum error; they never inherit AI mappings.
- The 90-credit graduation-project policy remains attached to the exact AI study-plan identifier and exact project course codes.
- The Fake University local adapter retains a compatibility fallback only for `ZU:IT:AI:P12`, allowing pre-foundation demo databases to keep working without creating a cross-major fallback.

## D. Already curriculum-generic runtime paths

- Catalog, progress, eligibility, recommendation, planner, degree-path, advisor, and conversation state use the resolved `study_plan_id` and its plan-course rows.
- Current-term offerings remain institution-wide operational data. They are filtered through curriculum membership when producing student academic-plan and course views.
- Grade semantics are institution-governed rather than curriculum-specific, so the verified Fake University grading policy is registered at institution scope while preserving exact-plan precedence.

## Deferred work and known boundaries

- Load and validate the 16 additional canonical curriculum datasets only after multi-code prerequisite values and `0000000` placeholders have an approved deterministic normalization policy.
- Seed relational curriculum identities and codes into a disposable local Supabase instance, then run real RLS/RPC integration tests. The migration was created and statically reviewed but was not executed.
- Redesign registration and administrative plan-change workflows so eligible curriculum selection is policy-driven and composite identity changes are atomic. The current integration safely rejects inconsistent identity instead of guessing.
- Backfill production-like student records only through a separately reviewed migration after local database validation. No production resource was touched in this slice.

## Acceptance boundary

The foundation is accepted locally when students in AI, Software Engineering, Nursing, and Law can share plan number `12` while resolving distinct plan keys, course memberships, and credit totals; unknown or ambiguous records fail closed; and AI-only policies do not activate for the other majors. This is covered by focused cross-repository regression tests.
