# Decision Trace Ledger — Proposed Canonical Recovery

Status: **APPROVED POLICY CONTRACT**

This document reconstructs a missing canonical companion contract from the P8
umbrella policy, the recovery draft, current deterministic/security contracts,
and repository implementation evidence. It does not retroactively establish
lost historical requirements or approve a new product capability.

## 1. Purpose and governing authority

The Decision Trace Ledger is an append-only, privacy-preserving audit sidecar
for material academic decisions. It records governed evidence and versions so a
decision can be inspected or replay-assessed without rewriting academic state.
It is governed by **AI EXPLAINS — DETERMINISTIC RULES DECIDE**: an LLM, a hash,
or a trace never authorizes or determines eligibility, progress, graduation,
registration, or another academic outcome.

Routine read-only domain/advisor operations may remain ephemeral. A trace is not
an official university record, enrollment transaction, or authorization grant.

## 2. Normative trace requirements

- A canonical typed entry carries identity, materiality, actor and subject scope,
  university scope, conditional student scope, deterministic engine/policy/source
  versions, outcome and input/scenario references, evidence references,
  provenance, timestamp, redaction, replay, supersession, limitations, and
  schema/hash versions.
- Materiality is a closed registry. Existing classes are `LEDGER_REQUIRED`,
  `LEDGER_OPTIONAL`, `DOMAIN_TRACE_ONLY`, and `NOT_LEDGERED`; changes require
  explicit policy approval.
- Canonicalization is deterministic: compact sorted-key UTF-8 JSON, normalized
  UTC timestamps, canonical enum values, and sorted set-like fields. The
  integrity hash is excluded from its own canonical payload and uses SHA-256.
  A SHA-256 digest is integrity evidence, not authorization or a signature.
- Evidence is typed and versioned. It must not contain chain-of-thought, raw
  prompts/completions, scratchpads, reasoning tokens, service credentials, or
  unnecessary student data.
- A student-individual entry requires the student scope; an institutional-period
  entry forbids it. Every tenant-scoped entry preserves university scope.
- Corrections append a new entry that supersedes the predecessor. Historical
  entries and their evidence are never rewritten.
- `EXACT_REPLAY` fails closed when historical source, engine, or policy versions
  are unavailable. `CURRENT_RECOMPUTATION` remains visibly distinct and cannot
  overwrite history. `NOT_REPLAYABLE` is explicit rather than inferred.
- Structural redaction removes or projects identity according to the permitted
  audience. A public/aggregate projection must disclose its redaction limitation.

## 3. Access and persistence boundaries

No browser client may arbitrarily write, update, or delete ledger/evidence
history. A trusted server-side persistence boundary may append only after the
authoritative deterministic result has been determined and validated. Evidence
inherits the authorization scope of its parent and cannot become an independent
enumeration path.

Individual viewing is a future surface and must require the verified student
owner or the existing complete advisor predicate: authenticated identity, active
`ACADEMIC_ADVISOR` membership, authoritative same university, and active exact
advisor-student assignment. Institutional analyst access never grants
student-level trace access. Cross-tenant access fails closed without existence
disclosure.

## 4. Current implementation status

**PARTIAL.** The repository contains a canonical decision-trace domain model,
validation, hashing, replay availability checks, typed evidence, immutable
PostgreSQL ledger/evidence persistence, a service-role append RPC, P6 outbox
records, and service-only outbox claim/complete/release/fail RPC boundaries.
The audited backend baseline is 1,488 passed, 0 failed, and 0 skipped.

This does not complete WC-040: no student-facing Decision History read API or
timeline is implemented, and the full P8 exit evidence, retention policy, and
viewer/projection design are not accepted by this document.

## 5. Open contracts — requires human approval

- Eligible material event registry expansion, retention/legal-erasure process,
  and any institutional viewer beyond the stated boundaries.
- Viewer API/projection shape, exact redaction profiles, and authorized export.
- Source/engine/policy-version preservation obligations for exact replay.
- Any additional chain/period integrity model beyond per-entry integrity.
- Any new persistence surface, grant, RLS policy, or external integration not
  already represented by the current audited implementation.

## 6. Non-goals and acceptance

The ledger does not grant academic authority, mutate recommendations/registration/
progress/catalog state, expose hidden reasoning, or replace official systems.
Future completion requires approved open contracts plus real local-Supabase
security evidence for grants/RLS/RPC, ownership/advisor/tenant isolation,
append-only behavior, evidence scope, integrity tamper handling, and replay.
