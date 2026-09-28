Status: **APPROVED POLICY CONTRACT**

# P8 Grounded Knowledge Verification Matrix

## Status and method

This remains a normative coverage matrix; it is not a claim that every row is
implemented. The historical recovery origin of the matrix remains relevant, but
the repository now includes later runtime slices for Decision Trace and structured
Policy Retrieval. `Existing` means an executable test currently exists; all other
rows remain proposed unless their implementation evidence is explicitly named.

Source codes: `U` = P8 umbrella policy; `S1` = Slice 1 model/canonical/validation/replay and `test_decision_trace.py`; `P6` = mock-registration RLS/threat contracts; `P7` = advisor authorization policy/service/migration; `CAP` = capability matrix.

## Current implementation evidence

The Student Decision History V1 backend baseline is **1,582 passed, 0 failed,
0 skipped** against Local Supabase. In addition to
the original Slice 1 evidence, the repository contains executable coverage for
Decision Trace persistence, P6 outbox mapping/processing boundaries, policy
domain/retrieval, atomic policy ingestion, student policy API, and Local Supabase
policy persistence/security, hybrid retrieval, grounded-answer guards, and
student-owner Decision History list/detail, redaction, integrity, and Local
Supabase browser-denial checks. That
evidence establishes implemented slices only;
it does not accept every row in this matrix or complete the P8 exit gate.

## Verified existing requirements and coverage

Slice 1 has executable focused tests for canonical entry validation, hashing,
tamper detection, supersession, scope checks, replay, and structural redaction.
The current audited root backend suite has zero skipped tests. Later P8 runtime
tests supplement, rather than replace, the original policy requirements.

## Requirements derived from implementation

The existing registries, immutable records, canonicalization, validation, replay helpers, and redaction projection determine the existing TRACE rows. P6/P7 authorization and suppression documents determine the draft database/security boundaries but do not constitute P8 runtime coverage.

## Proposed requirements and unresolved contracts

All rows marked `SPECIFIED` remain specification coverage only. Structured policy
persistence, ingestion, semantic and hybrid retrieval, and a bounded grounded
answer runtime are implemented, but document-source onboarding, broader graph registries, change-impact semantics,
approved institutional metric catalog, and query-provider controls remain
**OPEN CONTRACT / REQUIRES HUMAN APPROVAL**.

## Security and privacy boundaries

Candidate security rows require real local-Supabase tests where data access, grants, RLS, RPC, ownership, advisor assignment, tenant isolation, or suppression is involved. No unit-only evidence can accept those boundaries.

## Explicit non-goals

This matrix creates no executable test, migration, policy promotion, RAG corpus, graph runtime, impact engine, or institutional query engine.

| ID | Capability | Source | Input / precondition | Expected behavior | Security boundary | Test type | Existing coverage | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TRACE-01 | Envelope | S1 | Valid material entry | Canonical entry validates and hashes | No hidden reasoning | Unit | `P8_TRACE_001` | VERIFIED |
| TRACE-02 | Immutability | S1 | Existing entry | Historical object and stored rows cannot mutate | Append-only | Unit + Local Supabase | `002`, persistence trigger tests | VERIFIED |
| TRACE-03 | Materiality required | S1 | Required decision type | Maps to required | Closed registry | Unit | `003`; producer coverage remains separate | VERIFIED |
| TRACE-04 | Materiality optional | S1 | Formal policy consultation | Maps optional | Closed registry | Unit | `004` | VERIFIED |
| TRACE-05 | Domain-only | S1/U | Routine query | Not ledger-required | No accidental persistence | Unit | `005` | VERIFIED |
| TRACE-06 | Unsupported type | S1 | Unknown value | Fails closed | No arbitrary decision | Unit | `006` | VERIFIED |
| TRACE-07 | Canonical hash | S1 | Same logical payload | Stable canonical hash | Integrity only | Unit | `009-011,028` | VERIFIED |
| TRACE-08 | Tamper signal | S1 | Modified hashed entry | `TAMPER_DETECTED` | Integrity | Unit + viewer | `012-014`, history tamper tests | VERIFIED |
| TRACE-09 | Scope validation | S1 | Missing/mis-scoped student | Fails validation | Student scope | Unit + Local Supabase | `020-024,038`, owner/advisor tests | VERIFIED |
| TRACE-10 | Evidence normalization | S1 | Reordered/duplicate refs | Canonical evidence ordering | Provenance | Unit + Local Supabase | `026`, stored evidence-order tests | VERIFIED |
| TRACE-11 | Supersession | S1 | Correction to entry | New ID; predecessor unchanged | No historical rewrite | Unit + Local Supabase | `015-019`, persisted supersession tests | VERIFIED |
| TRACE-12 | Exact replay availability | S1 | All historic versions available | Availability contract true; no historical engine execution claimed | Version integrity | Unit | `029`, replay helper | VERIFIED |
| TRACE-13 | Replay fail-closed | S1 | Missing source/engine/policy | No substitute output | No fabricated replay | Unit | `030-035` | VERIFIED |
| TRACE-14 | Structural redaction | S1/U | Public aggregate projection | Student scope redacted | Privacy | Unit | `036,040`; no public viewer runtime | PARTIALLY VERIFIED |
| TRACE-15 | Persisted append boundary | U/P6/P7 | Service attempts valid append | Insert only; browser denied | RLS/RPC/tenant | Local Supabase adversarial | persistence, outbox, history local tests | VERIFIED |
| RAG-01 | Verified source admission | U | Unverified source | Reject/hold source | Provenance | Integration | None | SPECIFIED |
| RAG-02 | Citation anchor | U/S1 | Verified passage | Response names ID/version/locator | Evidence integrity | Integration | None | SPECIFIED |
| RAG-03 | Missing evidence | U | No matching passage | Explicit abstention | No fabrication | Integration | None | SPECIFIED |
| RAG-04 | Conflicting evidence | U | Conflicting verified sources | Preserve conflict/abstain | No silent authority | Integration | None | SPECIFIED |
| RAG-05 | Eligibility handoff | U | Eligibility question | Deterministic engine owns result | AI non-authority | Integration | None | SPECIFIED |
| RAG-06 | Progress handoff | U | Progress/graduation question | Deterministic engine owns result | AI non-authority | Integration | None | SPECIFIED |
| RAG-07 | Prompt injection in source | U | Malicious retrieved text | Ignore embedded instructions | Retrieval isolation | Security | None | SPECIFIED |
| RAG-08 | Prompt injection in query | U | User asks override/exfiltration | Reject unsafe request | Tool/secret boundary | Security | None | SPECIFIED |
| RAG-09 | Restricted source | Proposed | Restricted document | Citation/content policy enforced | Source classification | Integration | None | SPECIFIED |
| RAG-10 | Versioned source | U/S1 | Superseded source version | Cite exact version | Replay provenance | Integration | None | SPECIFIED |
| RAG-11 | Arabic locator | OPEN | Arabic source passage | Exact approved locator returned | Citation accuracy | Integration | None | SPECIFIED |
| RAG-12 | Student data exclusion | U | Policy query with student ID | No record retrieval | Ownership | Security | None | SPECIFIED |
| RAG-13 | Advisor case scope | U/P7 | Advisor combines policy + student | P7 predicate first | Assignment/tenant | Local integration | None | SPECIFIED |
| RAG-14 | Unsupported question | U | Outside corpus/metric | Abstain with limitation | Grounding | Integration | None | SPECIFIED |
| RAG-15 | No raw reasoning | S1/U | Generated answer/log | No CoT/raw prompt stored | Privacy/security | Unit/integration | `P8_TRACE_036` partial | SPECIFIED |
| IMPACT-01 | Policy delta | U | Versioned policy change | Read-only affected report | No write | Unit | None | SPECIFIED |
| IMPACT-02 | Curriculum delta | U | Curriculum revision | Affected plans reported | Tenant/scope | Unit | None | SPECIFIED |
| IMPACT-03 | Prerequisite delta | U | Rule change | recompute affected paths with uncertainty | Deterministic precedence | Unit | None | SPECIFIED |
| IMPACT-04 | Plan revision | U | Plan version change | Historic/current separated | No history rewrite | Unit | None | SPECIFIED |
| IMPACT-05 | Missing versions | S1/U | Historic source absent | Not-replayable limitation | No fabricated impact | Unit | `030-035` partial | SPECIFIED |
| IMPACT-06 | Owner/advisor scope | P7 | Individual impact request | Owner/P7 predicate enforced | BOLA/tenant | Local integration | None | SPECIFIED |
| IMPACT-07 | Analyst aggregate | P6/U | Small cohort impact | Suppress result | Privacy | Local integration | None | SPECIFIED |
| IMPACT-08 | No queue/write | U | Any impact run | No mutations/notifications | No side effect | Unit/audit | None | SPECIFIED |
| GRAPH-01 | Typed decision node | U/CAP | Material decision | Closed node kind/provenance | No raw reasoning | Unit | eligibility-only typed decision; no material-ledger adapter | PARTIALLY VERIFIED |
| GRAPH-02 | Rule/course/requirement links | U/CAP | Deterministic outcome | Typed causal edges | Engine precedence | Unit | eligibility course/prerequisite groups only; no requirement groups | PARTIALLY VERIFIED |
| GRAPH-03 | Evidence/source links | U/S1 | Evidence reference | Versioned source edge | Provenance | Unit | existing eligibility evidence; exact source versions absent and disclosed | PARTIALLY VERIFIED |
| GRAPH-04 | Cycle rejection | U/CAP | Edge closes cycle | Builder rejects | DAG integrity | Unit | `test_explainability_graph.py` | VERIFIED |
| GRAPH-05 | Scope mismatch | U/P7 | Cross-tenant edge | Reject | Tenant isolation | Unit | real owner-only API; no cross-tenant graph-edge namespace | PARTIALLY VERIFIED |
| GRAPH-06 | Missing evidence | U | Missing source | Explicit limitation node/state | No fabrication | Unit | exact-version limitation and review uncertainty tests | VERIFIED |
| GRAPH-07 | Student projection | U/S1 | Owner graph | Student-safe projection | Ownership | Local integration | authenticated student route and Local Supabase owned-profile test | VERIFIED |
| GRAPH-08 | Advisor/analyst projection | U/P7 | Advisor or analyst request | Assigned advisor allowed; analyst denied individual graph | Assignment/privacy | Local integration | no advisor/analyst graph route | SPECIFIED |
| QUERY-01 | Metric allowlist | U | Approved metric request | Typed permitted metric executes | No arbitrary query | Integration | None | SPECIFIED |
| QUERY-02 | Unsupported metric | U | Unknown metric | Abstain/reject | Allowlist | Integration | None | SPECIFIED |
| QUERY-03 | SQL injection | U | SQL-like natural language | No SQL execution | Database boundary | Security | None | SPECIFIED |
| QUERY-04 | Tenant binding | P6 | Analyst changes university | Server membership scope wins | Cross-tenant | Local integration | None | SPECIFIED |
| QUERY-05 | Suppression | P6/U | Below threshold cohort | Suppressed output/no raw counts | Inference resistance | Local integration | Existing P6 tests only | SPECIFIED |
| QUERY-06 | No student drill-down | U/P6 | Ask for student records | Reject/no identifiers | Privacy | Security | None | SPECIFIED |
| QUERY-07 | Grounded response | U/CAP | Metric/policy answer | Evidence, version, limitation shown | No hallucinated metric | Integration | None | SPECIFIED |
| QUERY-08 | Prompt injection | U | Override/debug/exfiltration request | Reject; no secret/SQL/raw rows | Model/tool boundary | Security | None | SPECIFIED |

## Specification acceptance gate

The 54 rows remain the normative scenario inventory. The repository now has additional
runtime and Local Supabase evidence for the implemented Decision Trace and
grounded Policy Retrieval slices. `TRACE-14` remains partially verified because
only the structural public-redaction helper exists; no public viewer is approved.
WC-007 now has a bounded eligibility-only runtime; GRAPH-01/02/03/05 remain
partial and GRAPH-08 is not implemented. WC-040 also remains partial because seven `LEDGER_REQUIRED` decision types lack
trusted runtime producers. Other RAG/IMPACT/GRAPH/QUERY rows still require the
stated approved design and tests.
P8 remains PARTIAL; the P8 exit gate is not accepted solely by the current
implementation.
