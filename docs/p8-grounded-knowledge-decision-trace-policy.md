# Phase P8.1 — Grounded Knowledge & Decision Trace Policy Gate

Policy Version: **1.0**
Phase: **P8.1 — Policy and Contracts Only**
Governing Principle: **AI Explains — Rules / Auditable Models Decide**
Status: **APPROVED POLICY CONTRACT**
Predecessor Phases: Phase 1–10 (Core Academic Stack), P3 (Student Intelligence), P4 (Decision Intelligence & Delay Consequence), P5 (Academic Digital Twin & What-If), P6 (Mock Registration & Institutional Demand), P7 (Advisor Copilot & Institutional Intelligence).

---

## 1. Scope of Phase P8 & Executive Summary

Phase P8 establishes the architectural policy, data contracts, and verification boundaries for **Grounded Knowledge and Decision Trace** across the Morshidi Academic Intelligence Operating System.

Morshidi operates under the strict foundational axiom:
\\text{AI Explains} \\quad \\text{---} \\quad \\text{Rules / Auditable Models Decide}

Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) pipelines must **NEVER** serve as authoritative sources for:
- Prerequisite evaluation,
- Degree eligibility,
- Academic requirement satisfaction,
- Graduation clearance,
- Official course registration,
- Course capacity or timetable facts,
- Individual student records or standing.

Phase P8.1 defines the formal, implementation-ready governance policies, data structures, boundaries, and validation contracts for:
1. **Decision Trace Ledger (WC-040)**: An append-only, privacy-preserving, cryptographically verifiable ledger envelope capturing material decisions with exact versions, provenance, and replayability.
2. **University Regulation RAG & Policy Retrieval (WC-038)**: An authoritative, cited retrieval boundary (\\InstitutionalPolicyProvider\\) that explains academic bylaws and regulations with exact source anchors, abstains when evidence is missing or conflicting, and strictly defers computable logic to deterministic engines.
3. **Academic Explainability Graph (WC-007)**: A typed Directed Acyclic Graph (DAG) formalizing the causal and evidential links between decisions, rules, factors, and policy passages.
4. **Change Impact Engine (WC-046)**: An analysis-only simulation and evaluation boundary calculating the downstream consequences of catalog, policy, and curriculum updates without writing to authoritative state.
5. **Institutional AI Query Experience (WC-039)**: A strictly constrained natural-language interface over the governed institutional metric catalog that forbids arbitrary SQL execution and prevents student record exposure.

---

## 2. Relationship to Phase P7

Phase P8 builds directly upon the accepted and locked outcomes of Phase P7:
- **P7.4 Advisor Authorization Gate**: Enforces authenticated identity, active \\ACADEMIC_ADVISOR\\ role, active explicit assignment record, and exact university match. P8 reuses this exact authorization boundary prior to exposing student-level traces or explainability subgraphs.
- **P7.5 Closed Advisor Copilot Read-Only Tools**: The 11 read-only deterministic tools provide the foundation for student academic state inspection, recommendations, and simulations. Routine tool queries remain ephemeral domain operations and are not persisted to the permanent ledger.
- **P7.1–P7.3 Institutional Intelligence**: Governed aggregate signals and threshold alerts establish the institutional scope boundaries inherited by P8.

---

## 3. Entry and Exit Gates

- **Entry Gate**: Acceptance of Phase P7 (Advisor Copilot, Human Review, Institutional Analytics). Satisfied by accepted commit \\4aab138\\.
- **Exit Gate**: Cited policy retrieval contracts, canonical ledger envelope, explainability DAG specifications, change impact analysis boundaries, institutional query constraints, and an exhaustive 54-scenario test matrix documented and verified.
- **Policy-Only Status**: Phase P8.1 is documentation and contract definition only. Zero database migrations, zero vector indexes, and zero runtime services are implemented in this phase.

---

## 4. Deterministic-Engine Precedence

Highest authority strictly supersedes lower layers. A lower layer can never override or relax a higher layer:
1. **Canonical Identity, Tenant Isolation & Authorization**: Authenticated identity, active role, explicit assignment, and exact university match.
2. **Phase 5 Academic Legality**: Prerequisite rules and eligibility decisions (\\ELIGIBLE\\, \\NOT_ELIGIBLE\\, \\REVIEW_REQUIRED\\).
3. **Phase 6 Academic Requirements**: Monotonic degree progress, completed credit hours, requirement groups, and audit status.
4. **Phase 7–9 Structural Policies**: Baseline recommendation priority tuples, planner constraints, and monotonic degree paths.
5. **Phase 4 Approved Deterministic Factors**: Verified student readiness and delay consequence indicators.
6. **User Optimization Preferences**: Explicit, bounded constraints (e.g., maximum credit hours) within allowed engine parameters.
7. **Institutional Policies & Regulations**: Textual bylaws and regulatory constraints ingested through \\InstitutionalPolicyProvider\\.
8. **AI Explanation & RAG**: Natural language synthesis of verified structured data and cited policy text.

---

## 5. Strict No-Write Boundaries

Phase P8.1 establishes that knowledge retrieval, explainability graph construction, and change impact evaluation are strictly **READ-ONLY / ANALYSIS-ONLY**:
- No evaluation can mutate student academic state, insert attempt records, alter course catalog entries, or create official SIS enrollments.
- Change impact evaluations identify affected decisions and flag recomputations without creating side-effecting mutations or automatic advisor queue records.
- Decision Trace Ledger recording occurs only as an append-only audit side-car for material milestone transactions, never rewriting existing historical records.

---

## 6. Privacy & Redaction Baseline

Phase P8 preserves the canonical privacy and suppression foundations established in Phase P6 (Institutional Demand Privacy Policy) and Phase P7:
- **Aggregate-First Access**: Institutional queries operate exclusively on aggregate metrics. Individual student identities, records, and attempts are completely excluded.
- **Suppression Integration**: Governed queries inherit the versioned \\minimum_disclosure_group_size\\ policy (integer \\(\\ge 2\\), with synthetic sandbox default 3). Counts below the threshold return \\SUPPRESSED\\ with reason \\DEMAND_PRIVACY_SUPPRESSED\\ and quality flag \\SUPPRESSED_FOR_PRIVACY\\.
- **Role-Scoped Redaction**: Individual student ledger entries are accessible exclusively to the student themselves (\\STUDENT_SAFE\\) or their actively assigned academic advisor (\\ADVISOR_SAFE\\). Institutional analysts have zero access to student-level traces.

---

## 7. Policy-Only Status Declaration

This document and its companion P8 specifications constitute formal policy and contract evidence. Under the Critical Status Rule:
- No capability status advances solely due to policy documentation.
- \\WC-007\\ (Academic Explainability Graph) remains \\PARTIALLY_ENABLED\\.
- \\WC-038\\ (University Regulation RAG) remains \\PARTIALLY_ENABLED\\.
- \\WC-039\\ (Institutional AI Query Experience) remains \\PLANNED\\.
- \\WC-040\\ (Decision Trace Ledger) remains \\PARTIALLY_ENABLED\\.
- \\WC-046\\ (Change Impact Engine) remains \\PARTIALLY_ENABLED\\.
- Proposal obligation \\PROP-072\\ remains \\MISSING\\.

---

## 8. Companion Policy Documents

The detailed specifications governing Phase P8 are established in:
1. [decision-trace-ledger-policy.md](decision-trace-ledger-policy.md): Canonical envelope, material decisions, replay modes, tamper evidence, and authorization.
2. [institutional-policy-retrieval-policy.md](institutional-policy-retrieval-policy.md): InstitutionalPolicyProvider, chunking, citations, engine precedence, and prompt-injection defense.
3. [academic-explainability-graph-policy.md](academic-explainability-graph-policy.md): Typed node and edge taxonomies, DAG cycle prevention, and role-based projection.
4. [change-impact-policy.md](change-impact-policy.md): Analysis-only version diff evaluation, affected decision identification, and no-write guarantees.
5. [institutional-ai-query-policy.md](institutional-ai-query-policy.md): Governed metric catalog, zero arbitrary SQL, zero student drill-down, and suppression enforcement.
6. [p8-grounded-knowledge-test-matrix.md](p8-grounded-knowledge-test-matrix.md): Exhaustive 54-scenario closed verification matrix.

---

## 9. Future Runtime Implementation Roadmap

Runtime implementation of Phase P8 capabilities will be executed in future runtime phases:
- **Future P8 Runtime Implementation**: Implementation of append-only ledger tables, RLS policies, canonical JSON serialization, and cryptographic hashing utilities.
- **Future P8 Runtime Implementation**: Implementation of InstitutionalPolicyProvider adapters, vector index integration, citation extraction, and engine handoff logic.
- **Future P8 Runtime Implementation**: Implementation of explainability DAG builder services, change impact batch evaluators, and constrained metric query planners.
