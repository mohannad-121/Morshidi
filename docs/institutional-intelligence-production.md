# Institutional Intelligence Production Contract (V2)

Date: 2026-10-19  
Status: implemented locally; release blocked pending real local database validation and human-approved release.

## Authority boundary

Institutional Intelligence is a read-only decision-support layer. AI may select an approved tool and explain its typed output. AI never calculates eligibility, demand, capacity, progress, bottleneck scores, or simulation effects. All metrics are computed by `app.institutional_analytics.engine` from an immutable aggregate snapshot.

There is no database-to-database connection to Fake University. Morshidi reads synchronized academic state from its own Supabase database and reads current offering/capacity facts through the existing Fake University HTTP contract. No Institutional Intelligence endpoint mutates registrations, offerings, plans, attempts, or academic rules.

## Composite curriculum identity

Every program uses `ZU:{faculty_code}:{major_code}:P{plan_number}`. Plan Number 12 is never used alone. Shared course metrics are rolled up university-wide while retaining `demand_by_program` and faculty/program attribution.

## Deterministic metric definitions

- `CURRENT_REGISTERED`: authoritative current offering enrollment when a complete offering snapshot exists; otherwise the count of synchronized `IN_PROGRESS` attempts, with the fallback identified in `inputs.source`.
- `ELIGIBLE_NOT_REGISTERED`: distinct students whose plan contains the course, who have neither completed nor registered it, and whose verified prerequisite groups are satisfied.
- `PLANNED_NEED`: distinct students selecting the course in their latest active, valid mock-registration plan for the target term.
- `DEGREE_PATH_NEED`: distinct students who can reach the course now or after completing one currently eligible verified prerequisite step. Unresolved/source-conflict groups never qualify.
- `PROJECTED_DEMAND`: distinct-student union of eligible-now, planner-selected, and degree-path-upcoming sets, excluding completed/currently registered students. The three component counts remain visible and are not summed blindly.
- `OFFERED_SEATS`, `AVAILABLE_SEATS`, and utilization: exact course rollups across sections from a complete offering snapshot. Missing/incomplete supply remains `UNAVAILABLE`, never zero.
- `DEMAND_CAPACITY_GAP`: projected demand minus offered seats when both inputs are available.
- `PROGRESS`: earned credits divided by authoritative plan required credits, capped at 100%, grouped into `0–24`, `25–49`, `50–74`, `75–89`, and `90–100` bands.
- `BLOCKED_DEGREE_PATH`: a student has incomplete required courses and no remaining required course is currently eligible under verified rules.
- `REVIEW_REQUIRED`: unresolved/source-conflict prerequisite logic. The system behavior is always `FAIL_CLOSED`.

## Capacity states

- `UNDER_CAPACITY`: projected demand is below 50% of offered capacity.
- `HEALTHY`: 50% through less than 85%.
- `NEAR_CAPACITY`: 85% through 100%.
- `OVER_DEMAND`: projected demand exceeds offered seats.
- `UNAVAILABLE`: capacity facts are incomplete or unavailable.

Thresholds exist only in the backend engine; UI code displays the returned state.

## Transparent bottleneck score

The older P7 contract prohibited an opaque composite score. The approved V2 contract introduces a transparent 0–100 score while retaining every raw factor and reason code:

- required/core role: 25 points;
- verified downstream impact: 5 points per downstream course, capped at 25;
- positive capacity-gap share: up to 30 points;
- affected-student share: up to 20 points.

Levels are `NONE` (0–24), `WATCH` (25–49), `HIGH` (50–74), and `CRITICAL` (75–100). Review-required prerequisite relationships are never converted into verified graph edges.

## Privacy and authorization

- `INSTITUTIONAL_ANALYST` is the existing institution-admin-equivalent role and receives institution scope.
- `ACADEMIC_ADVISOR` receives only explicitly assigned students from `advisor_student_assignments`.
- Ordinary students receive stable HTTP 403.
- API DTOs contain no owner IDs, profile IDs, names, emails, raw diagnostic answers, transcripts, or raw attempts.
- Program progress distributions and derived progress statistics are suppressed below the configurable minimum cohort size. Aggregate program headcount remains visible so sparse reality is not misrepresented as zero.
- Responses use `Cache-Control: private, no-store`.

## Institutional Copilot tools

The model may select exactly one of:

`get_institution_overview`, `get_program_metrics`, `get_course_demand`, `get_bottlenecks`, `get_capacity_pressure`, `get_progress_distribution`, `get_review_queue`, or `simulate_section_capacity`.

Tool arguments are schema-bound. Free SQL, raw student requests, credentials, and mutations are rejected. Tool output is returned unchanged alongside a deterministic short summary. Explicit previous tool/course fields provide bounded follow-up context.

## Performance design

Catalog, profiles, attempts, and plan intents load through five parallel PostgREST requests. Each request paginates in 1,000-row pages, so the 1,155-membership catalog cannot be silently truncated. Computation is one in-memory pass over the immutable snapshot; there are no per-student network calls. Current offerings are fetched once per request and are not cached, preventing stale authoritative registration state.

No database migration or persistent analytics table is required.
