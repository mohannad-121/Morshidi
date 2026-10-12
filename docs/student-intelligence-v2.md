# Student Intelligence V2

Status: implemented local review slice; diagnostic migration is unapplied.

## Deterministic boundary

Student Intelligence V2 personalizes explanations, modeled difficulty, eligible-course ranking, and planner tie-breaking. It never changes prerequisite truth, eligibility, completed credits, requirement satisfaction, graduation truth, or the legal course graph. The LLM receives only a bounded summary after deterministic engines return their structured result. Raw diagnostic answers are never sent to the LLM.

## Evidence hierarchy and fusion

`EVIDENCE_FUSION_V1` keeps three evidence classes separate:

1. `OFFICIAL_VERIFIED_UNIVERSITY_PERFORMANCE` is accepted only when provenance and verification state are verified and a scope-matched grade policy exists.
2. `COMPLETED_QUICK_DIAGNOSTIC` is a modeled baseline. In-progress and abandoned sessions contribute nothing.
3. User-stated preferences are displayed separately and never create or increase mastery.

For each skill, diagnostic evidence is used alone when no official evidence exists. With one or two official course observations, official evidence has weight 0.70. With three or more, it has weight 0.90. The latest authoritative repeat is used for current mastery; earlier failures and repeat history remain risk evidence. Scores, confidence, counts, contributing courses/domains, sources, and reason codes remain visible.

## Versions

- Profile: `STUDENT_INTELLIGENCE_PROFILE_V2`
- Taxonomy: `MORSHIDI_SKILL_TAXONOMY_V2`
- Plan mapping: `PLAN12_COURSE_SKILLS_V2`
- Grade policy: `FAKE_UNIVERSITY_GRADING_POLICY_V1`
- Fusion: `EVIDENCE_FUSION_V1`
- Cold start: `COLD_START_POLICY_V1`
- Assessment: `QUICK_DIAGNOSTIC_V1`
- Selection: `DIAGNOSTIC_SELECTION_V1`
- Scoring: `DIAGNOSTIC_SCORING_V1`

## Taxonomy and grade policy

The taxonomy explicitly classifies all 68 courses in the active Plan 12 seed. It is a Morshidi curriculum classification, not an institutional statement of learning outcomes. Runtime course-name substring inference is prohibited.

Fake University publishes the authoritative `FAKE_UNIVERSITY_GRADING_POLICY_V1` contract: GPA 0–100 with scale 100, and course numeric grades 0–100. Morshidi accepts that version only with those exact semantics. The complete grades policy, every numeric value, and profile/grades GPA consistency are validated before any academic write. Values are finite `Decimal`-safe facts; they are neither clamped nor converted, and PASSED/FAILED remains the university's supplied outcome.

`GradePolicyRegistry` supports this contract only for the exact Fake University institution and Plan 12. That application definition is insufficient by itself: each official attempt must also carry the strictly parsed durable reference `university:<university_id>:grading-policy:FAKE_UNIVERSITY_GRADING_POLICY_V1`. Missing, malformed, wrong-institution, and wrong-version references fail closed. Existing matched attempts are reconciled in place on the first valid post-contract sync, preserving attempt ID and sequence while refreshing authoritative performance fields. The existing `performance_source_reference` column is sufficient; no grading migration is required.

## Diagnostic policy

The Arabic-first bank contains 25 original multiple-choice items: five each for programming reasoning, logical problem solving, quantitative math, statistics/data reasoning, and theory/comprehension/memory. Selection is reproducible: two balanced base items per domain, a typical target of 12, and up to 16 when estimates remain ambiguous. The browser submits only the currently issued question ID and option ID. It never receives correctness, difficulty weights, or the answer key.

Difficulty-weighted correctness produces a whole-number domain score. Two responses can only be low confidence; three are at most medium; high confidence requires at least four consistent responses. This is an auditable heuristic baseline, not a validated psychometric instrument and not an official academic result.

## Persistence and privacy

Migration `20261011190000_add_student_diagnostic_v1.sql` adds owner/profile/institution/plan-scoped sessions, responses, and completed domain results. Scope is derived server-side. RLS is enabled, browser roles have no table mutation privileges, and only the service role may execute the atomic answer RPC. The RPC locks the session, accepts only the currently issued question, rejects duplicate answers, and makes completed/abandoned sessions immutable. Only the latest completed valid assessment version participates in fusion.

## Cold start and invalidation

No verified numeric grades yields `COLD_START_NO_PERFORMANCE_EVIDENCE`; limited breadth yields `LOW_ACADEMIC_EVIDENCE`; sufficient breadth yields `ESTABLISHED_ACADEMIC_EVIDENCE`. The diagnostic is recommended but never required. The source fingerprint includes the profile update, deterministic attempt ordering and values, performance provenance, verification state, policy-bound source reference, and latest completed diagnostic version/time. Trusting an old record after policy-bound resync therefore changes the snapshot whenever mastery changes.

## Limitations

The current preference projection is intentionally empty until the existing conversation-memory store exposes an approved bounded read contract; no user statement is reinterpreted as ability. When no scope-matched governed grade policy is configured, V2 reports `official_grade_mastery=UNAVAILABLE_UNVERIFIED_POLICY` in its limitations and creates no official grade mastery. The migration requires local database integration and adversarial RLS/RPC testing before production application. Modeled scores are not scientifically validated and must not be presented as university evaluation.

Degree-path ordering does not consume Student Intelligence V2 in this slice. That integration is explicitly `NOT_IMPLEMENTED`; the UI must not claim otherwise. Existing deterministic degree-path graph and legal sequence rules are unchanged.
