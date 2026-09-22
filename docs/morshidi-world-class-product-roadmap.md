# Morshidi World-Class Product Roadmap

## Purpose

This document locks the product direction beyond baseline proposal compliance. Morshidi's north star is an Arabic-first, evidence-grounded academic decision platform that lets students understand choices, lets advisors review recommendations, and lets institutions anticipate structural demand. Proposal compliance remains a mandatory, separately tracked delivery stream in `proposal-compliance-roadmap.md`.

Every capability must satisfy two definitions of done: its own acceptance criteria in the capability matrix and any linked proposal obligations. A world-class feature never substitutes for an unmet proposal requirement.

## Product principles

1. AI explains governed evidence; it does not invent academic facts or silently make institutional decisions.
2. Simulation is read-only until a person explicitly performs a transaction in an authoritative university system.
3. Equivalent inputs, data versions, and policy versions must yield reproducible results and traceable evidence.
4. Eligibility, readiness, recommendation, registration intent, and confirmed registration are distinct states.
5. Synthetic data can prove workflow and engineering behavior, never real-world validity or institutional readiness.
6. The same capability contract must operate against synthetic, file-based, and institutional providers; only the adapter and evidence authority change.
7. Student-facing recommendations must expose uncertainty, constraints, alternatives, and escalation paths.
8. Institutional analytics use minimum-necessary, privacy-preserving aggregates and role-scoped access.
9. Morshidi will not create a deceptive overall “best student” score. Separate academic signals retain their meaning.

## Classification and priority

Each `WC-*` capability has exactly one primary class:

- `CORE_DIFFERENTIATOR`: decision intelligence central to the product promise.
- `INSTITUTIONAL_DIFFERENTIATOR`: advisor, curriculum, and institution-level intelligence.
- `ADVANCED_DATA_DEPENDENT`: valuable intelligence whose validity depends on longitudinal or externally governed data.
- `SCALE_AND_INTEGRATION`: portability, provider, and production-scale foundations.
- `EXPERIENCE_DIFFERENTIATOR`: accessible, explainable student and staff experiences.
- `DEMO_AND_EVALUATION`: safe demonstration, research evaluation, and adoption evidence.

Priorities mean `P0` critical path, `P1` near-term differentiator, `P2` later high value, and `P3` future scale or research. Priority does not override a proposal requirement.

## Dependency architecture

```text
P3 deterministic intelligence
  -> P4 Decision Intelligence Integration
     -> WC-004 Delay Consequence Intelligence
        -> WC-001 Academic Digital Twin
           -> WC-002 What-If Simulator
              -> WC-003 Scenario Comparison

WC-008 Mock Registration
  -> WC-009 Institutional Demand
     -> WC-010 Capacity Intelligence
        -> WC-054 Institutional Simulation

WC-029 Curriculum Ingestion
  -> WC-030 Multi-Plan
     -> WC-031 Multi-Major
        -> WC-032 Multi-University
           -> WC-035 SIS and WC-036 SSO adapters

WC-034 Synthetic Data and Providers
  -> WC-033 Sandbox University
     -> WC-050 Proposal Evidence and Demo Mode
        -> WC-051 Evaluation Lab
           -> WC-052 Real Student Pilot (real-data gate)
```

Cross-cutting prerequisites are WC-040 decision trace, WC-041 data quality, WC-044 privacy and student controls, WC-048 accessible Arabic-first PWA, and WC-053 observability.

## Product surfaces

### Student decision environment

The Academic Digital Twin composes verified records, plan rules, prerequisites, progress, structural warnings, and evidence versions into a student-owned read model. What-if scenarios are isolated branches that compare choices without altering records. Delay Consequence Intelligence explains critical-path effects. Graduation Audit distinguishes completed, in-progress, eligible, blocked, and unresolved requirements. Mock Registration records intent only and never impersonates official registration.

The visual roadmap, explainability graph, goal modes, modeled reports, notifications, offline snapshot, and accessible Arabic-first PWA turn the same governed decisions into an understandable experience. Career, skills, internship, portfolio, and predictive features remain explicitly bounded by their data quality and validation gates.

### Advisor and institutional environment

Advisor Copilot summarizes evidence and alternatives but does not replace human judgment. Recommendations and overrides are attributable and feed an academic review queue. Institutional Analytics, demand, bottleneck, capacity, cohort, curriculum-health, accreditation, data-quality, and simulation views use role-scoped aggregates. Student-level access remains purpose-bound.

### Data, policy, and integration environment

Curriculum ingestion normalizes versioned plans without erasing source provenance. Equivalency and version-transition logic require authoritative institutional rules. Multi-plan is the first portability milestone; multi-major and multi-university follow only after plan isolation is proven. Regulation RAG may retrieve and cite policies, but deterministic engines remain authoritative for computable rules.

Provider boundaries are defined in `morshidi-external-adapter-strategy.md`. Sandbox behavior is defined in `morshidi-sandbox-university-spec.md`. The canonical scope and definitions of done are in `morshidi-world-class-capability-matrix.md`.

## Synthetic, file-based, and real-data strategy

Four declarations are used in the matrix:

- `FULLY_BUILDABLE_LOCALLY`: no external source is required for meaningful completion.
- `DEMO_WITH_SYNTHETIC_DATA`: workflow can be demonstrated, but claims are explicitly synthetic.
- `REQUIRES_REAL_DATA_FOR_VALIDATION`: implementation can begin locally, but accuracy or usefulness cannot be validated without representative governed data.
- `REQUIRES_INSTITUTIONAL_INTEGRATION`: completion depends on an authoritative institutional service or agreement.

Synthetic providers implement the same contracts as real adapters and carry synthetic provenance on every record. CSV imports are controlled acquisition adapters, not an alternate domain model. Switching providers must not change decision semantics, privacy rules, evidence requirements, or user-visible uncertainty.

## Scope normalization and feature-bloat review

The registry preserves every requested outcome while removing duplicate product surfaces. Offerings, timetable, and campus/location intelligence share one provider-backed capability; privacy-preserving analytics and student data controls share one governance capability; curriculum health and curriculum sandbox share one committee workflow; one-click and modeled graduation reports share one report capability; synthetic students and synthetic providers share one fixture suite; evaluation and feedback share one lab; proposal evidence and demo mode share one verification surface; and accessibility, Arabic-first mobile behavior, and PWA delivery share one experience capability.

The review intentionally rejects parallel chatbots, vendor-specific domain forks, duplicate dashboards, a global student score, and separate synthetic-only business logic. Only nine capabilities are P0. Predictive, career, internship, accreditation, multi-university, SIS, SSO, and real-pilot work remains behind explicit data, governance, or institutional gates. This keeps the roadmap ambitious without allowing speculative features to displace the deterministic decision core or mandatory proposal closure.

## Simulation and transaction boundary

Digital-twin, what-if, mock-registration, curriculum-sandbox, and institutional-simulation operations are immutable scenarios. They may produce recommendations, forecasts, and registration intent, but never update authoritative academic history, official schedules, enrollment, or degree status. A future transactional integration requires explicit confirmation, idempotency, authorization, audit logging, reconciliation, and an institutional API contract.

## Privacy, governance, and safety

All capabilities inherit authentication, owner isolation, least privilege, evidence provenance, retention, and redaction requirements. Institution views default to aggregate data with suppression thresholds. Consent and data controls disclose purpose and source. Predictive models require subgroup evaluation, calibration, drift monitoring, documented limitations, and human appeal. Generated explanations must cite decision facts and must not expose raw private records in logs or prompts.

## Demo, evaluation, and pilot policy

Demo Mode is visibly synthetic, resettable, deterministic, and separated from production identities. The Product Evaluation Lab measures task success, explanation comprehension, trust calibration, accessibility, Arabic usability, and advisor workload. A real student pilot requires ethics and institutional approval, informed consent, data minimization, incident response, support ownership, success criteria, and an exit plan. Synthetic results cannot be reported as pilot evidence.

## Expanded delivery sequence

The world-class roadmap contains thirteen future phases. Phase boundaries are gates, not calendar promises.

| Phase | Outcome | Entry gate | Exit evidence |
|---|---|---|---|
| P4 | Decision Intelligence Integration and specialized Delay Consequence | P3 engines are stable; P4.1 policy approved | **Implemented:** baseline-preserving readiness composition, annotations, typed trace, specialized delay engine, and regression evidence |
| P5 | Digital Twin, general What-If, Scenario Comparison | P4.2 closure; immutable snapshot and provenance contracts | **Pure domain implemented:** immutable fingerprinted scenarios, three-operation evaluator, P4 Delay reuse, 16 typed deltas, same-base factual comparison, and 51-scenario evidence; authorized API/UI remains |
| P6 | Mock Registration, Demand, Bottlenecks | P5 | **P6.1 policy gate locked:** intent/registration separation, revision/current-intent semantics, descriptive demand metrics, privacy suppression, and supplied-fact capacity comparison; pure implementation remains P6.2 |
| P7 | Advisor Copilot, Human Review, Institutional Analytics | P6 | Role-scoped review workflow and aggregate dashboards |
| P8 | Grounded Knowledge and Decision Trace | P7 | Cited policy retrieval and replayable trace ledger |
| P9 | Arabic UX, Visual Roadmap, Reports, Accessibility, PWA | P8 | WCAG/RTL/usability acceptance and modeled exports |
| P10 | Offerings, Capacity, Registration, Calendar, Timetable | Provider contracts available | Adapter conformance with clear authority boundaries |
| P11 | Skills, Career, Internship, Portfolio, Workload | Valid datasets approved | Validation reports and uncertainty disclosures |
| P12 | Curriculum Ingestion, Versions, Equivalency, Multi-Plan/Major | P9 | Versioned imports and cross-plan isolation tests |
| P13 | Multi-University Provider Architecture | P12 | Second-institution conformance without domain forks |
| P14 | Evaluation, Consent, Evidence, Real Pilot | Prior safety gates | Approved protocol and measured pilot outcomes |
| P15 | Production SIS, SSO, Institutional Integration | Agreements and security review | Reconciliation, audit, access, and failover evidence |
| P16 | Hardening, Observability, Sandbox, Demo | Production topology known | SLOs, runbooks, recovery drills, repeatable demonstration |

## Immediate next phase

After P4.2 closure, the next eligible phase is **P5 — Digital Twin and general What-If**. P5 may reuse P4 immutable snapshot provenance, Decision Trace, readiness-aware composition, annotations, specialized Delay Consequence, and the external Phase 9 comparison adapter. It must first define scenario identity/lifecycle, cloning and isolation, current-versus-modeled semantics, authorization/privacy, deterministic comparison, and no-write acceptance tests. No predictive model, institutional adapter, or transaction may bypass those gates.

### P5.1 policy gate evidence

P5.1 defines the documentation-only implementation gate in `academic-digital-twin-policy.md`, `what-if-simulator-policy.md`, `scenario-comparison-policy.md`, and the operation, delta, and test matrices. V1 is ephemeral and domain-only: one authoritative base, at most one structural operation plus one existing-policy constraint bundle, and at most two comparison sides. Supported structural operations are modeled course completion and P4 Delay Consequence omission; modeled failure/withdrawal, live availability, major/plan transition, equivalency creation, transactions, and predictive claims remain deferred or forbidden.

This policy evidence does not implement WC-001, WC-002, or WC-003 and does not change their statuses. P5.2 must prove immutable cloning, engine reuse, modeled/history separation, bounded deterministic deltas/comparison, and full Phase 5–9/P3/P4 regression before implementation evidence may be claimed. API, persistence, frontend, saved scenarios, and registration remain later decisions.

### P5.2 implementation evidence

P5.2 implements the pure, ephemeral Academic Digital Twin and What-If package with immutable normalized state, privacy-minimized SHA-256 fingerprints, stale-state rejection, one structural operation plus one typed constraint bundle, exact P5.1.1 satisfied-elective rejection, unchanged Phase 5–9/P4 reuse, all 16 deltas, and bounded factual comparison. The implementation trace maps all 51 committed scenarios. `WC-001` and `WC-002` remain `PARTIALLY_ENABLED`; `WC-003` advances to `PARTIALLY_ENABLED`. Product completion still requires an authorized service boundary and Arabic student experience; persistence, Mock Registration, offerings, and transactions remain later phases.

### P6.1 policy gate evidence

P6.1 defines Mock Registration as explicit, non-binding student intent and separates it from Digital Twin scenarios, planner/recommendation output, and official registration. The contract locks deterministic revisions and current-intent resolution, Phase 5/6-backed atomic validation, exact-period descriptive aggregation, nine finite demand metrics, aggregate-first privacy suppression, coverage/provenance flags, optional supplied-fact capacity arithmetic, and a 64-scenario implementation gate. Missing offerings/capacity never become false zeros or inferred unavailability. P6.2 is pure/domain-only; persistence, APIs, auth roles, SIS adapters, frontend, actual-registration comparison, forecasting, bottleneck ranking, section estimation, and institutional actions remain later slices. Policy evidence changes no WC status.

## Governance

Changes to a WC record require a documented rationale, dependency review, proposal crosswalk review, data classification, and updated definition of done. A capability may move from `EXTERNAL_DEPENDENCY` only when its named evidence or integration gate is met. No status in the proposal compliance matrix is changed by this roadmap lock.
