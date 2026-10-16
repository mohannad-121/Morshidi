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
- Transitional assessment: `QUICK_DIAGNOSTIC_V1`
- Current assessment: `QUICK_DIAGNOSTIC_V2`
- Transitional selection/scoring: `DIAGNOSTIC_SELECTION_V1` / `DIAGNOSTIC_SCORING_V1`
- Current selection/scoring: `DIAGNOSTIC_SELECTION_V2` / `DIAGNOSTIC_SCORING_V2`

## Taxonomy and grade policy

The taxonomy explicitly classifies all 68 courses in the active Plan 12 seed. It is a Morshidi curriculum classification, not an institutional statement of learning outcomes. Runtime course-name substring inference is prohibited.

Fake University publishes the authoritative `FAKE_UNIVERSITY_GRADING_POLICY_V1` contract: GPA 0–100 with scale 100, and course numeric grades 0–100. Morshidi accepts that version only with those exact semantics. The complete grades policy, every numeric value, and profile/grades GPA consistency are validated before any academic write. Values are finite `Decimal`-safe facts; they are neither clamped nor converted, and PASSED/FAILED remains the university's supplied outcome.

`GradePolicyRegistry` supports this contract only for the exact Fake University institution and Plan 12. That application definition is insufficient by itself: each official attempt must also carry the strictly parsed durable reference `university:<university_id>:grading-policy:FAKE_UNIVERSITY_GRADING_POLICY_V1`. Missing, malformed, wrong-institution, and wrong-version references fail closed. Existing matched attempts are reconciled in place on the first valid post-contract sync, preserving attempt ID and sequence while refreshing authoritative performance fields. The existing `performance_source_reference` column is sufficient; no grading migration is required.

## Diagnostic policy

`QUICK_DIAGNOSTIC_V2` is an Arabic-first fixed 30-question academic-reasoning diagnostic: exactly six items in each of programming reasoning, logical problem solving, quantitative/mathematical reasoning, statistics/data reasoning, and theory/conceptual understanding. Every domain contains exactly two easy, two medium, and two hard items. Each server-only item records skill, subskill, correct answer, distractor rationales, cognitive operation, evidence weight, expected solving behavior, and estimated time. The browser receives only the current ID, Arabic/English prompt, and options; it never receives domain, difficulty, correctness, distractor meaning, weights, or answer keys.

The browser submits the currently issued question/option plus bounded response time and the student's LOW/MEDIUM/HIGH self-confidence. The atomic RPC requires exactly 30 unique issued answers, six per domain, and two per difficulty/domain. Self-confidence is evidence about calibration, never correctness and never model confidence.

### Exact deterministic scoring formula

For an answered item `i`, `w_i = difficulty_weight × evidence_weight`, where difficulty weights are EASY `1.0`, MEDIUM `1.5`, and HARD `2.0`. `base = 100 × Σ(correct_i × w_i) / Σ(w_i)`. Timing reliability is `max(0.70, 1 - 0.05 × implausibly_fast_item_count)`. Split-half consistency is `max(0.75, 1 - 0.25 × |accuracy_first_three - accuracy_last_three|)`. The published whole-number score is `round(50 + (base - 50) × timing_reliability × consistency)`, bounded to 0–100. Weak-quality evidence is therefore shrunk toward neutral rather than automatically punished.

Model confidence is LOW if coverage is incomplete or global anti-gaming flags show unrealistically fast/repetitive behavior; HIGH requires complete difficulty coverage, no fast items, no quality flags, and bounded split-half consistency; otherwise it is MEDIUM. Anti-gaming flags cover incomplete sessions, unrealistically fast completion, repetitive option selection, contradictory cross-domain performance, and random-looking answer transitions. They lower evidence confidence, never academic eligibility or official standing. Bounded reasoning-pattern codes describe only behavior visible in this diagnostic (for example careful-but-slower or confidence above observed evidence); they are not personality or intelligence labels.

## Persistence and privacy

Migration `20261011190000_add_student_diagnostic_v1.sql` adds owner/profile/institution/plan-scoped sessions, responses, and completed domain results. Scope is derived server-side. RLS is enabled, browser roles have no table mutation privileges, and only the service role may execute the atomic answer RPC. The RPC locks the session, accepts only the currently issued question, rejects duplicate answers, and makes completed/abandoned sessions immutable. Only the latest completed valid assessment version participates in fusion.

### Expand/deploy/contract rollout

Migration `20261016090000_upgrade_student_diagnostic_v2.sql` is an expand-only transition. It retains the service-role-only nine-argument V1 answer RPC and adds the eleven-argument V2 overload. Unversioned status/start requests retain V1 semantics for the deployed frontend; the V2 frontend explicitly requests `QUICK_DIAGNOSTIC_V2`. The backend always selects scoring and RPC behavior from the stored session version. Missing timing/confidence is accepted only for V1, while values supplied for V1 are ignored rather than reinterpreted as genuine evidence. An active V1 session is resumed without conversion and may complete under its original bank, adaptive selection, scoring, and provenance.

A later, separately reviewed contract migration may remove the V1 RPC overload and the V1 HTTP transition path only after production shows zero `QUICK_DIAGNOSTIC_V1` sessions with `status = 'IN_PROGRESS'` and telemetry confirms normal V2 adoption. This release must not perform that cleanup.

## Cold start and invalidation

No verified numeric grades yields `COLD_START_NO_PERFORMANCE_EVIDENCE`; limited breadth yields `LOW_ACADEMIC_EVIDENCE`; sufficient breadth yields `ESTABLISHED_ACADEMIC_EVIDENCE`. The diagnostic is recommended but never required. The source fingerprint includes the profile update, deterministic attempt ordering and values, performance provenance, verification state, policy-bound source reference, and latest completed diagnostic version/time. Trusting an old record after policy-bound resync therefore changes the snapshot whenever mastery changes.

## Limitations

The current preference projection is intentionally empty until the existing conversation-memory store exposes an approved bounded read contract; no user statement is reinterpreted as ability. When no scope-matched governed grade policy is configured, V2 reports `official_grade_mastery=UNAVAILABLE_UNVERIFIED_POLICY` in its limitations and creates no official grade mastery. The migration requires local database integration and adversarial RLS/RPC testing before production application. Modeled scores are not scientifically validated and must not be presented as university evaluation.

Degree-path ordering does not consume Student Intelligence V2 in this slice. That integration is explicitly `NOT_IMPLEMENTED`; the UI must not claim otherwise. Existing deterministic degree-path graph and legal sequence rules are unchanged.
