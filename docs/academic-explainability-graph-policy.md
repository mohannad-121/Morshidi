# Academic Explainability Graph — Proposed Canonical Recovery

Status: **APPROVED POLICY CONTRACT**

WC-007 is a distinct capability: a typed directed acyclic graph (DAG)
connecting decisions, rules, factors, requirements, evidence, and sources. A
Decision Trace, an engine reason code, or a citation is not by itself an
Academic Explainability Graph implementation.

## 1. Normative boundaries

- The graph explains governed deterministic results; it never becomes an engine
  for eligibility, progress, planning, registration, or other academic decisions.
- Nodes and edges need stable identities, provenance, version/scope context, and
  a display-safe/redaction classification. They must never carry hidden reasoning,
  service credentials, or unbounded student data.
- Causal/evidentiary edges must remain typed and directed. A graph builder must
  reject a relationship that produces a causal DAG cycle.
- Every child relation must preserve or narrow its parent university/student
  scope; cross-tenant references fail closed.
- Missing or unavailable evidence is explicit. The graph must not fabricate a
  node, edge, source, or causal explanation.
- Student projection requires verified ownership. Advisor projection requires the
  complete P7 advisor predicate. Institutional analysts receive no individual
  graph; any aggregate treatment requires separately approved suppression-safe
  design.

## 2. Eligibility Explainability Graph V1

**PARTIAL RUNTIME: ELIGIBILITY ONLY.** A pure, closed-type builder projects the
existing Phase 5 `CanTakeDecision` without rerunning or changing it. It emits
stable non-student-identifying node IDs, sorted nodes/edges, a bounded DAG, and
typed `DECISION`, `COURSE`, `REASON`, `PREREQUISITE_GROUP`, `ACADEMIC_STATE`, and
`LIMITATION` nodes. Directed relations are closed: `DECIDED_BY`, `REFERENCES`,
`SUPPORTED_BY`, `SATISFIED_BY`, `BLOCKED_BY`, and `LIMITED_BY`. Option sets remain
OR within each prerequisite group; separate groups remain AND. `NOT_PASSED`
means only that the evaluator has no passing attempt for that option, not a
fabricated failed/in-progress/not-attempted state.

The authenticated student-only `GET /api/v1/me/eligibility/{course_code}/explanation-graph`
derives plan, attempts, and ownership from the existing self-service route. It
supports `WHY`, and `WHY_NOT ELIGIBLE` only where the current deterministic
result already supplies blockers; it does not simulate changed facts. The
existing eligibility page shows an Arabic-first, read-only structured graph
below the authoritative result. No advisor or analyst graph route exists.

The current `CanTakeDecision` does **not** expose exact source or policy version
IDs or approved policy-text locators. V1 therefore returns empty version lists
and the explicit `EXACT_SOURCE_VERSION_UNAVAILABLE` limitation. It never
pretends prerequisite facts came from WC-038 RAG or a Decision Trace ledger
record. It includes current-state and non-official-registration limitations.
Review-required outcomes preserve unresolved/conflicting/incomplete model
reasons and never become eligibility decisions. There is no database table,
migration, stored graph, LLM-generated node, or graph-triggered write.

## 3. Open contracts — requires human approval

- Expansion beyond the closed eligibility V1 registries, including causal
  traversal or supersession relations.
- Exact source/policy version propagation from authoritative engines, and any
  persisted graph identity/migration strategy.
- Graph builders for progress, recommendations, planning, degree paths, or
  material ledger decisions; V1 does not claim those.
- Advisor projection and any separately approved aggregate disclosure design.
- Whether recommendation and policy-retrieval evidence share a graph namespace.

## 4. Non-goals and acceptance

V1 does not provide a graph database, automatic edge mining, arbitrary traversal,
counterfactual simulation, advisor graph, analyst graph, or an LLM explanation
builder. Broader WC-007 acceptance still requires approved and verified graph
adapters for other deterministic engines, exact provenance when available,
scope/redaction gates for any new viewer, and no hidden reasoning.
