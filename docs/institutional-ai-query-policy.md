# Institutional AI Query Experience — Proposed Canonical Recovery

Status: **APPROVED POLICY CONTRACT**

WC-039 is a constrained natural-language experience over a governed institutional
metric catalog. It is distinct from Advisor Copilot, student advisor features,
and the existing deterministic Institutional Intelligence endpoints.

## 1. Normative boundaries

- Natural language may map only to a finite, approved metric catalog with typed
  parameters and permitted aggregations. Unsupported requests abstain.
- The experience may call only approved server-side metric/service adapters. It
  must never emit, execute, or accept arbitrary SQL, table names, raw filters,
  debug exports, unrestricted database access, or browser-held service secrets.
- Each response identifies the metric definition/version, effective university
  and period scope, deterministic provenance, quality/suppression state, and
  limitations or uncertainty.
- University scope comes from active server-side institutional membership; client
  parameters cannot widen it or reveal unavailable tenants/records.
- Existing minimum-disclosure policy applies after the full filter. Suppressed
  results reveal no raw rows, bypass counts, individual identifiers, attempts,
  GPA, traces, scenarios, conversations, or low-cohort aggregates.
- AI may phrase governed metric output and cited policy evidence. It cannot
  manufacture values, infer individual records, mutate state, or decide academic
  legality.
- User/retrieved-content prompt injection cannot expand the metric allowlist,
  actor role, tenant scope, or response fields.

## 2. Current implementation status

**PLANNED.** The repository has aggregate-first, tenant-scoped Institutional
Demand/Institutional Intelligence services and suppression-aware authorization
boundaries. It has no WC-039 natural-language query planner, approved metric
catalog for NL access, SQL executor, dedicated response surface, or WC-039 test
suite. Existing institutional endpoints are not evidence of this capability.

## 3. Open contracts — requires human approval

- Approved metrics, dimensions, periods, parameter schema, and reconciliation
  rules.
- Authorized institutional roles beyond the present membership model.
- Rate limits, query-cost controls, audit retention, disclosure/differencing
  controls, and response-review workflow.
- Model/provider selection, Arabic query semantics, and grounding/evaluation
  corpus.

## 4. Non-goals and acceptance

This recovery does not authorize NL-to-SQL, a database agent, unrestricted
exports, dashboards, predictive claims, or student-level institutional search.
Future acceptance requires an approved finite catalog and response schema plus
tests for allowlist and injection rejection, tenant binding, suppression, no
individual fields, grounding/abstention, and deterministic metric parity.
