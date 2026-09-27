# Academic Explainability Graph — Proposed Canonical Recovery

Status: **APPROVED POLICY CONTRACT**

WC-007 is a distinct future capability: a typed directed acyclic graph (DAG)
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

## 2. Current implementation status

**PLANNED.** Current deterministic engines, Decision Trace records, and policy
citations provide potential inputs only. The repository has no graph node/edge
schema, builder, traversal API, persistence model, visualization, or graph
projection surface. The roadmap capability-matrix label `PARTIALLY_ENABLED` is
not runtime evidence and does not change this implementation status.

## 3. Open contracts — requires human approval

- Closed node and edge registries, including whether limitation and supersession
  relations participate in causal traversal.
- Identity/versioning rules, persistence model, graph namespace boundaries, and
  migration strategy.
- Traversal depth/size limits, caching, cycle-detection semantics, and display
  rendering rules.
- Exact student/advisor redaction profiles and aggregate disclosure controls.
- Whether recommendation and policy-retrieval evidence share a graph namespace.

## 4. Non-goals and acceptance

No graph database, graph API, automatic edge mining, visualization, or runtime
builder is authorized by this recovery. Future acceptance requires approved type
and access registries plus tests for determinism, cycle/scope rejection, missing
evidence, provenance, student/advisor projections, analyst denial, and absence
of hidden reasoning.
