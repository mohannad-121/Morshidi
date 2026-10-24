"""Pure deterministic degree path planning engine (Phase 9.2).

No FastAPI, Starlette, Supabase, httpx, or I/O dependency is permitted in this module.
It reuses Phase 5 (via Phase 7/8), Phase 6 (calculate_academic_progress), Phase 7
(recommend_courses), and Phase 8 (plan_semester) without mutating state or duplicating logic.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from time import monotonic
from typing import Callable

from app.degree_path.models import (
    DegreePathStrategy,
    STRATEGY_LABELS_AR,
    canonical_semantic_fingerprint,
    are_paths_materially_distinct,
    deduplicate_candidate_paths,
    DEFAULT_BEAM_WIDTH,
    DEFAULT_CANDIDATE_WINDOW_SIZE,
    DEFAULT_COMBINATION_EVALUATION_LIMIT,
    DEFAULT_SEMESTER_BRANCH_WIDTH,
    DEGREE_PATH_POLICY_VERSION,
    PLANNING_SCOPE,
    BlockerType,
    DegreePathConstraintError,
    DegreePathConstraints,
    DegreePathCreditSummary,
    DegreePathFreeElectiveRequirement,
    DegreePathIntegrityError,
    DegreePathOption,
    DegreePathResult,
    UnplacedCreditBreakdown,
    UnplacedCreditReason,
    ModeledSemesterEntry,
    PathReasonCode,
    PathStatus,
    deterministic_path_id,
)
from app.degree_path.validation import validate_degree_path_result
from app.planner.engine import plan_semester
from app.planner.models import (
    PlanReasonCode,
    PlannerConstraints,
    SemesterPlannerResult,
)
from app.progress.engine import calculate_academic_progress
from app.progress.models import (
    AcademicProgress,
    AcademicProgressCatalog,
    CourseProgressState,
    RequirementType,
)
from app.recommendations.engine import recommend_courses
from app.recommendations.models import RecommendationCandidate, RecommendationResult
from app.rules.evaluator import evaluate_can_take
from app.rules.models import (
    AttemptOutcome,
    CanTakeCatalog,
    CanTakeDecision,
    CanTakeRequest,
    Decision,
    DecisionReason,
    StudentCourseAttempt,
)

# ---------------------------------------------------------------------------
# Metadata & Disclaimers
# ---------------------------------------------------------------------------

_METHODOLOGY_NOTE = (
    "These degree path options are deterministic multi-semester course sequences generated from "
    "your verified academic study plan, degree progress state, and planning preferences. "
    "They indicate modeled registration trajectories that could advance your degree progress "
    "under the simulation assumption that selected courses pass at the end of each modeled semester. "
    "They do not constitute official university registration approval, do not predict actual "
    "graduation dates or academic standing, do not guarantee course availability or timetable "
    "compatibility, and do not reflect institutional academic advising."
)

_LIMITATIONS: tuple[str, ...] = (
    "Planning is bounded strictly by modeled academic study plan structure.",
    "Simulation assumes selected future courses pass with AttemptOutcome.PASSED at the conclusion of each modeled semester; this is an exploratory simulation assumption, not an outcome prediction.",
    "Persisted IN_PROGRESS courses are conservatively treated as unresolved and do not satisfy downstream prerequisites during simulation.",
    "Beam search with beam_width=3 prunes search branches; output is a deterministic bounded search result, not guaranteed globally optimal across all unexamined branches.",
    "Single-semester combinations use a top-M=15 candidate window and a deterministic 256-state frontier; this prevents exponential subset expansion and is not guaranteed globally optimal.",
    "Course availability, seasonal offering patterns, section capacities, and weekly timetables are not modeled.",
    "No GPA prediction or academic standing forecast is performed.",
    "Does not predict or guarantee an official university graduation date.",
    "Does not constitute official institutional graduation clearance or academic advising.",
)


def _free_elective_requirements(progress: AcademicProgress) -> tuple[DegreePathFreeElectiveRequirement, ...]:
    courses_by_group = {
        group.group_id: tuple(course for course in progress.courses if course.requirement_group_id == group.group_id)
        for group in progress.requirement_groups
        if group.requirement_type is RequirementType.FREE_ELECTIVE
    }
    return tuple(
        DegreePathFreeElectiveRequirement(
            group_code=group.group_code,
            name_ar=group.name_ar,
            name_en=group.name_en,
            required_credits=group.required_credits,
            completed_credits=group.credited_toward_requirement,
            current_credits=group.in_progress_credited_toward_requirement,
            remaining_credits_after_current=max(
                group.remaining_required_credits - group.in_progress_credited_toward_requirement,
                Decimal("0"),
            ),
            selection_state=group.free_elective_selection_state.value,
            completed_course_codes=tuple(sorted(
                course.course_code for course in courses_by_group[group.group_id]
                if course.satisfies_free_elective and course.state is CourseProgressState.COMPLETED
            )),
            current_course_codes=tuple(sorted(
                course.course_code for course in courses_by_group[group.group_id]
                if course.satisfies_free_elective and course.state is CourseProgressState.IN_PROGRESS
            )),
        )
        for group in progress.requirement_groups
        if group.requirement_type is RequirementType.FREE_ELECTIVE
    )


def _unplaced_credit_breakdown(
    progress: AcademicProgress,
    *,
    total_unplaced_credits: Decimal,
    unplaced_course_codes: tuple[str, ...],
    blocker_codes: tuple[str, ...],
) -> tuple[UnplacedCreditBreakdown, ...]:
    """Partition final unplaced credits by canonical requirement group exactly once."""
    unplaced = set(unplaced_course_codes)
    courses_by_group = {
        group.group_id: tuple(
            course for course in progress.courses
            if course.requirement_group_id == group.group_id
            and course.course_code in unplaced
        )
        for group in progress.requirement_groups
    }
    entries: list[UnplacedCreditBreakdown] = []
    credits_left = total_unplaced_credits
    for group in progress.requirement_groups:
        credits = min(
            max(
                group.remaining_required_credits - group.in_progress_credited_toward_requirement,
                Decimal("0"),
            ),
            credits_left,
        )
        courses = courses_by_group[group.group_id]
        if credits > 0:
            if (
                group.requirement_type is RequirementType.FREE_ELECTIVE
                and group.free_elective_selection_state.value == "FREE_ELECTIVE_POLICY_REQUIRED"
            ):
                reason = UnplacedCreditReason.FREE_ELECTIVE_POLICY_REQUIRED
            elif group.requirement_type is RequirementType.REQUIRED:
                reason = UnplacedCreditReason.UNSCHEDULED_REQUIRED_CREDITS
            else:
                reason = UnplacedCreditReason.UNSCHEDULED_ELECTIVE_CREDITS
            entries.append(UnplacedCreditBreakdown(
                reason=reason,
                credits=credits,
                requirement_group_code=group.group_code,
                course_codes=tuple(sorted(course.course_code for course in courses)),
                evidence_codes=tuple(sorted(set(blocker_codes))),
                actionable=reason is not UnplacedCreditReason.FREE_ELECTIVE_POLICY_REQUIRED,
            ))
            credits_left -= credits
        for course in courses:
            if course.credit_hours == 0:
                entries.append(UnplacedCreditBreakdown(
                    reason=UnplacedCreditReason.MANDATORY_ZERO_CREDIT_REQUIREMENT,
                    credits=Decimal("0"),
                    requirement_group_code=group.group_code,
                    course_codes=(course.course_code,),
                    evidence_codes=tuple(sorted(set(blocker_codes))),
                    actionable=True,
                ))
    if credits_left > 0:
        entries.append(UnplacedCreditBreakdown(
            reason=UnplacedCreditReason.UNMODELED_PLAN_CREDITS,
            credits=credits_left,
            requirement_group_code="UNMODELED_PLAN_TOTAL",
            course_codes=(),
            evidence_codes=tuple(sorted(set(blocker_codes))),
            actionable=False,
        ))
    return tuple(entries)


# ---------------------------------------------------------------------------
# Internal Search State
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PathState:
    depth: int
    accumulated_attempts: tuple[StudentCourseAttempt, ...]
    academic_progress: AcademicProgress
    selected_semesters: tuple[ModeledSemesterEntry, ...]
    unresolved_blocker_codes: tuple[str, ...]
    canonical_path_codes: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class _BlockerEvidence:
    """Positive, course-level evidence for terminal path diagnostics."""

    review_required_codes: frozenset[str]
    current_in_progress_codes: frozenset[str]
    prerequisite_locked_codes: frozenset[str]
    plan_constraints_too_restrictive: bool = False
    candidate_window_exclusion: bool = False

    @property
    def diagnostic_codes(self) -> tuple[str, ...]:
        codes: list[str] = []
        if self.review_required_codes:
            codes.append(BlockerType.REVIEW_REQUIRED_BLOCKER.value)
        if self.current_in_progress_codes:
            codes.append(BlockerType.CURRENT_IN_PROGRESS_BLOCKER.value)
        if self.prerequisite_locked_codes:
            codes.append(BlockerType.PREREQUISITES_LOCKED.value)
        if self.plan_constraints_too_restrictive:
            codes.append(BlockerType.PLAN_CONSTRAINTS_TOO_RESTRICTIVE.value)
        if self.candidate_window_exclusion:
            codes.append(BlockerType.CANDIDATE_WINDOW_EXCLUSION.value)
        return tuple(sorted(codes))


def _completed_passed_codes(progress: AcademicProgress) -> frozenset[str]:
    return frozenset(
        cp.course_code
        for cp in progress.courses
        if cp.state is CourseProgressState.COMPLETED
    )


def _remaining_modeled_requirement_codes(progress: AcademicProgress) -> frozenset[str]:
    """Return incomplete plan courses that belong to currently unsatisfied groups."""
    unsatisfied_group_ids = {
        group.group_id for group in progress.requirement_groups if not group.is_satisfied
    }
    return frozenset(
        course.course_code
        for course in progress.courses
        if course.state is not CourseProgressState.COMPLETED
        and course.requirement_group_id in unsatisfied_group_ids
    )


def _candidate_fits_active_constraints(
    candidate: RecommendationCandidate,
    constraints: DegreePathConstraints,
) -> bool:
    """Prove that a candidate can form a valid one-course semester by constraints alone."""
    return (
        candidate.credit_hours <= constraints.max_credit_hours_per_semester
        and (
            constraints.max_courses_per_semester is None
            or constraints.max_courses_per_semester >= 1
        )
    )


def _collect_blocker_evidence(
    progress: AcademicProgress,
    eligibility_catalog: CanTakeCatalog,
    attempts: tuple[StudentCourseAttempt, ...],
    recommendations: RecommendationResult,
    constraints: DegreePathConstraints,
    planner_result: SemesterPlannerResult | None = None,
) -> _BlockerEvidence:
    """Classify blockers only from positive evidence already produced by Phases 5-8."""
    relevant_codes = _remaining_modeled_requirement_codes(progress)

    review_required_codes = frozenset(
        course.course_code
        for course in recommendations.review_required_courses
        if course.course_code in relevant_codes
    )
    current_in_progress_codes = frozenset(
        code for code in recommendations.excluded_in_progress if code in relevant_codes
    )

    prerequisite_locked: set[str] = set()
    for code in sorted(relevant_codes):
        decision = evaluate_can_take(
            eligibility_catalog,
            CanTakeRequest(
                study_plan_id=eligibility_catalog.study_plan_id,
                target_course_code=code,
                student_attempts=attempts,
            ),
        )
        if (
            isinstance(decision, CanTakeDecision)
            and decision.decision is Decision.NOT_ELIGIBLE
            and DecisionReason.MISSING_PREREQUISITE_GROUP in decision.reasons
        ):
            prerequisite_locked.add(code)

    plan_constraints_too_restrictive = False
    candidate_window_exclusion = False
    if (
        planner_result is not None
        and planner_result.valid_combination_count == 0
        and not planner_result.plan_options
    ):
        ranked = recommendations.ranked_recommendations
        fitting_candidates = tuple(
            candidate
            for candidate in ranked
            if _candidate_fits_active_constraints(candidate, constraints)
        )
        plan_constraints_too_restrictive = bool(ranked) and not fitting_candidates

        outside_window = ranked[planner_result.candidate_window_size :]
        candidate_window_exclusion = any(
            _candidate_fits_active_constraints(candidate, constraints)
            for candidate in outside_window
        )

    return _BlockerEvidence(
        review_required_codes=review_required_codes,
        current_in_progress_codes=current_in_progress_codes,
        prerequisite_locked_codes=frozenset(prerequisite_locked),
        plan_constraints_too_restrictive=plan_constraints_too_restrictive,
        candidate_window_exclusion=candidate_window_exclusion,
    )


def _partial_priority_tuple(
    state: _PathState,
    initial_progress: AcademicProgress,
) -> tuple[int, int, Decimal, int, int, int, tuple[tuple[str, ...], ...]]:
    """Lexicographic priority tuple for intermediate beam search ordering (Phase 9.1 §24)."""
    is_complete = 1 if state.academic_progress.all_modeled_plan_requirements_satisfied else 0
    depth = state.depth
    modeled_credits_delta = (
        state.academic_progress.completed_plan_credits
        - initial_progress.completed_plan_credits
    )
    satisfied_groups_count = (
        state.academic_progress.satisfied_requirement_group_count
        - initial_progress.satisfied_requirement_group_count
    )
    blocker_count = len(state.unresolved_blocker_codes)
    aggregate_rank_sum = sum(s.plan_option.rank for s in state.selected_semesters)
    canonical_path_codes = state.canonical_path_codes

    return (
        -is_complete,
        depth,
        -modeled_credits_delta,
        -satisfied_groups_count,
        blocker_count,
        aggregate_rank_sum,
        canonical_path_codes,
    )


# ---------------------------------------------------------------------------
# Pure Engine Entry Point
# ---------------------------------------------------------------------------



def _plan_multi_strategy_degree_paths(
    progress_catalog: AcademicProgressCatalog,
    eligibility_catalog: CanTakeCatalog,
    student_attempts: tuple[StudentCourseAttempt, ...],
    constraints: DegreePathConstraints,
    *,
    beam_width: int = DEFAULT_BEAM_WIDTH,
    semester_branch_width: int = DEFAULT_SEMESTER_BRANCH_WIDTH,
    reported_cumulative_gpa: Decimal | None = None,
    reported_gpa_scale: Decimal | None = None,
    reported_earned_credit_hours: Decimal | None = None,
    check_budget: Callable[[], None] | None = None,
    metrics: dict[str, float | int] | None = None,
) -> DegreePathResult:
    req_max = constraints.max_credit_hours_per_semester
    strategy_definitions = [
        (
            DegreePathStrategy.FASTEST.value,
            STRATEGY_LABELS_AR[DegreePathStrategy.FASTEST.value],
            req_max,
        ),
        (
            DegreePathStrategy.BALANCED.value,
            STRATEGY_LABELS_AR[DegreePathStrategy.BALANCED.value],
            min(Decimal("15"), req_max)
            if req_max > Decimal("15")
            else max(Decimal("12"), req_max - Decimal("3")),
        ),
        (
            DegreePathStrategy.LIGHTER.value,
            STRATEGY_LABELS_AR[DegreePathStrategy.LIGHTER.value],
            min(Decimal("12"), req_max),
        ),
    ]

    candidate_paths: list[DegreePathOption] = []
    base_result: DegreePathResult | None = None

    for strat_code, label_ar, cap_credits in strategy_definitions:
        if check_budget is not None:
            check_budget()
        strat_constraints = replace(
            constraints,
            max_credit_hours_per_semester=cap_credits,
            max_paths=1,
            multi_strategy=False,
        )
        strat_res = plan_degree_paths(
            progress_catalog=progress_catalog,
            eligibility_catalog=eligibility_catalog,
            student_attempts=student_attempts,
            constraints=strat_constraints,
            beam_width=beam_width,
            semester_branch_width=semester_branch_width,
            reported_cumulative_gpa=reported_cumulative_gpa,
            reported_gpa_scale=reported_gpa_scale,
            reported_earned_credit_hours=reported_earned_credit_hours,
            check_budget=check_budget,
            metrics=metrics,
        )
        if base_result is None:
            base_result = strat_res
        if strat_res.paths:
            opt = strat_res.paths[0]
            candidate_paths.append(replace(opt, strategy=strat_code, strategy_name_ar=label_ar))

    deduped = deduplicate_candidate_paths(candidate_paths)
    final_paths = tuple(
        replace(opt, rank=idx)
        for idx, opt in enumerate(deduped[:constraints.max_paths], start=1)
    )

    if base_result is None:
        raise DegreePathIntegrityError("Failed to initialize baseline degree path result")

    result = DegreePathResult(
        study_plan_id=base_result.study_plan_id,
        degree_path_policy_version=base_result.degree_path_policy_version,
        planning_scope=base_result.planning_scope,
        constraints=constraints,
        paths=final_paths,
        initial_completed_credits=base_result.initial_completed_credits,
        initial_remaining_credits=base_result.initial_remaining_credits,
        initial_satisfied_group_count=base_result.initial_satisfied_group_count,
        total_requirement_group_count=base_result.total_requirement_group_count,
        unresolved_review_required_courses=base_result.unresolved_review_required_courses,
        persisted_in_progress_courses=base_result.persisted_in_progress_courses,
        total_parent_states_expanded=base_result.total_parent_states_expanded,
        methodology_note=base_result.methodology_note,
        limitations=base_result.limitations,
    )
    validate_degree_path_result(
        progress_catalog,
        eligibility_catalog,
        student_attempts,
        result,
        reported_cumulative_gpa=reported_cumulative_gpa,
        reported_gpa_scale=reported_gpa_scale,
        reported_earned_credit_hours=reported_earned_credit_hours,
    )
    return result

def plan_degree_paths(
    progress_catalog: AcademicProgressCatalog,
    eligibility_catalog: CanTakeCatalog,
    student_attempts: tuple[StudentCourseAttempt, ...],
    constraints: DegreePathConstraints,
    *,
    beam_width: int = DEFAULT_BEAM_WIDTH,
    semester_branch_width: int = DEFAULT_SEMESTER_BRANCH_WIDTH,
    reported_cumulative_gpa: Decimal | None = None,
    reported_gpa_scale: Decimal | None = None,
    reported_earned_credit_hours: Decimal | None = None,
    check_budget: Callable[[], None] | None = None,
    metrics: dict[str, float | int] | None = None,
) -> DegreePathResult:
    """Generate and rank multi-semester degree paths deterministically.

    Parameters
    ----------
    progress_catalog:
        The AcademicProgressCatalog for the student's study plan.
    eligibility_catalog:
        The CanTakeCatalog containing verified plan-course rules.
    student_attempts:
        Immutable tuple of persisted student course attempts.
    constraints:
        User planning preferences (credit limits, course limits, horizon, max paths).
    beam_width:
        Engine search safety configuration: partial paths retained at each depth (default 3).
    semester_branch_width:
        Engine search safety configuration: Phase 8 options generated per state (default 3).
    reported_cumulative_gpa, reported_gpa_scale, reported_earned_credit_hours:
        Passed through to Phase 6 as reported facts. Not used for ranking.
    """
    study_plan_id = progress_catalog.study_plan.study_plan_id

    def record(name: str, started: float) -> None:
        if metrics is not None:
            metrics[name] = metrics.get(name, 0) + (monotonic() - started) * 1000

    if check_budget is not None:
        check_budget()

    # 1. Structural Integrity Checks
    if eligibility_catalog.study_plan_id != study_plan_id:
        raise DegreePathIntegrityError("Mismatched study_plan_id between progress and eligibility catalogs")

    if constraints.multi_strategy and constraints.max_paths > 1:
        return _plan_multi_strategy_degree_paths(
            progress_catalog=progress_catalog,
            eligibility_catalog=eligibility_catalog,
            student_attempts=student_attempts,
            constraints=constraints,
            beam_width=beam_width,
            semester_branch_width=semester_branch_width,
            reported_cumulative_gpa=reported_cumulative_gpa,
            reported_gpa_scale=reported_gpa_scale,
            reported_earned_credit_hours=reported_earned_credit_hours,
            check_budget=check_budget,
            metrics=metrics,
        )

    if isinstance(beam_width, bool) or not isinstance(beam_width, int):
        raise DegreePathConstraintError("beam_width must be an integer")
    if beam_width < 1:
        raise DegreePathConstraintError("beam_width must be at least 1")

    if isinstance(semester_branch_width, bool) or not isinstance(semester_branch_width, int):
        raise DegreePathConstraintError("semester_branch_width must be an integer")
    if semester_branch_width < 1:
        raise DegreePathConstraintError("semester_branch_width must be at least 1")

    # 2. Initial Academic Progress Baseline
    phase_started = monotonic()
    initial_progress = calculate_academic_progress(
        progress_catalog,
        student_attempts,
        reported_cumulative_gpa=reported_cumulative_gpa,
        reported_gpa_scale=reported_gpa_scale,
        reported_earned_credit_hours=reported_earned_credit_hours,
    )
    record("initial_progress_ms", phase_started)

    persisted_in_progress = tuple(
        sorted(
            set(
                cp.course_code
                for cp in initial_progress.courses
                if cp.state is CourseProgressState.IN_PROGRESS
            )
        )
    )
    completed_course_codes = tuple(sorted(_completed_passed_codes(initial_progress)))
    current_course_codes = persisted_in_progress
    canonical_total_credits = progress_catalog.study_plan.total_credit_hours
    current_plan_credits = initial_progress.in_progress_plan_credits

    # Initial recommendation result to identify global review-required courses
    phase_started = monotonic()
    initial_rec = recommend_courses(
        progress_catalog,
        eligibility_catalog,
        student_attempts,
        reported_cumulative_gpa=reported_cumulative_gpa,
        reported_gpa_scale=reported_gpa_scale,
        reported_earned_credit_hours=reported_earned_credit_hours,
    )
    record("recommendations_ms", phase_started)
    unresolved_review_required = tuple(
        sorted(rc.course_code for rc in initial_rec.review_required_courses)
    )

    # 3. Zero-Semester Completed Student Edge Case
    if initial_progress.all_modeled_plan_requirements_satisfied:
        priority_tuple = (
            -1,  # P1: completion_rank = 1
            0,   # P2: semester_count = 0
            Decimal("0"),  # -P3
            0,   # -P4
            0,   # P5: unresolved blockers
            0,   # P6: aggregate rank sum
            (),  # P7: canonical path codes
        )
        single_path = DegreePathOption(
            path_id=deterministic_path_id(study_plan_id, ()),
            rank=1,
            status=PathStatus.MODELED_COMPLETE,
            semesters=(),
            semester_count=0,
            total_planned_courses=0,
            total_planned_credits=Decimal("0"),
            completed_plan_credit_delta=Decimal("0"),
            final_completed_plan_credits=initial_progress.completed_plan_credits,
            final_remaining_plan_credits=initial_progress.remaining_plan_credits,
            newly_satisfied_requirement_group_count=0,
            newly_satisfied_requirement_group_codes=(),
            remaining_required_course_codes=(),
            unresolved_blocker_codes=(),
            aggregate_semester_rank_sum=0,
            priority_tuple=priority_tuple,
            reason_codes=(PathReasonCode.REACHES_MODELED_PLAN_COMPLETION,),
            completed_course_codes=completed_course_codes,
            current_course_codes=current_course_codes,
            unplaced_course_codes=(),
            credit_summary=DegreePathCreditSummary(
                degree_required_credits=canonical_total_credits,
                completed_credits=initial_progress.completed_plan_credits,
                current_credits=current_plan_credits,
                future_placed_credits=Decimal("0"),
                unplaced_credits=Decimal("0"),
            ),
            free_elective_requirements=_free_elective_requirements(initial_progress),
            unplaced_credit_breakdown=(),
        )
        completed_result = DegreePathResult(
            study_plan_id=study_plan_id,
            degree_path_policy_version=DEGREE_PATH_POLICY_VERSION,
            planning_scope=PLANNING_SCOPE,
            constraints=constraints,
            paths=(single_path,),
            initial_completed_credits=initial_progress.completed_plan_credits,
            initial_remaining_credits=initial_progress.remaining_plan_credits,
            initial_satisfied_group_count=initial_progress.satisfied_requirement_group_count,
            total_requirement_group_count=initial_progress.total_requirement_group_count,
            unresolved_review_required_courses=unresolved_review_required,
            persisted_in_progress_courses=persisted_in_progress,
            total_parent_states_expanded=0,
            methodology_note=_METHODOLOGY_NOTE,
            limitations=_LIMITATIONS,
        )
        phase_started = monotonic()
        validate_degree_path_result(
            progress_catalog,
            eligibility_catalog,
            student_attempts,
            completed_result,
            reported_cumulative_gpa=reported_cumulative_gpa,
            reported_gpa_scale=reported_gpa_scale,
            reported_earned_credit_hours=reported_earned_credit_hours,
        )
        record("validation_ms", phase_started)
        return completed_result

    # 4. Search State Setup
    initial_state = _PathState(
        depth=0,
        accumulated_attempts=student_attempts,
        academic_progress=initial_progress,
        selected_semesters=(),
        unresolved_blocker_codes=(),
        canonical_path_codes=(),
    )

    # Registry of visited canonical states for depth-aware collision resolution
    # state_key -> (minimum_depth, best_partial_priority_tuple)
    seen_states: dict[tuple[frozenset[str], frozenset[str]], tuple[int, tuple]] = {}
    init_key = (
        _completed_passed_codes(initial_progress),
        frozenset(persisted_in_progress),
    )
    seen_states[init_key] = (0, _partial_priority_tuple(initial_state, initial_progress))

    active_beam: list[_PathState] = [initial_state]
    finalized_states: list[tuple[_PathState, PathStatus, tuple[str, ...]]] = []
    total_parent_states_expanded = 0

    # Index study plan required courses for blocker diagnostics
    plan_courses_by_code = {pc.course_code: pc for pc in progress_catalog.plan_courses}
    group_by_id = {rg.group_id: rg for rg in progress_catalog.requirement_groups}

    # 5. Deterministic Beam Search Loop
    search_started = monotonic()
    while active_beam:
        if check_budget is not None:
            check_budget()
        candidates_to_expand: list[_PathState] = []

        # Check termination conditions for current beam states
        for state in active_beam:
            # Priority 1: Modeled Complete
            if state.academic_progress.all_modeled_plan_requirements_satisfied:
                finalized_states.append((state, PathStatus.MODELED_COMPLETE, state.unresolved_blocker_codes))
                continue

            # Priority 2: Horizon Reached
            if state.depth == constraints.max_semesters_ahead:
                # Gather final-state blocker diagnostics
                phase_started = monotonic()
                final_rec = recommend_courses(
                    progress_catalog,
                    eligibility_catalog,
                    state.accumulated_attempts,
                    reported_cumulative_gpa=reported_cumulative_gpa,
                    reported_gpa_scale=reported_gpa_scale,
                    reported_earned_credit_hours=reported_earned_credit_hours,
                )
                evidence = _collect_blocker_evidence(
                    state.academic_progress,
                    eligibility_catalog,
                    state.accumulated_attempts,
                    final_rec,
                    constraints,
                )
                record("blocker_diagnostics_ms", phase_started)

                finalized_states.append(
                    (state, PathStatus.HORIZON_REACHED, evidence.diagnostic_codes)
                )
                continue

            # State needs expansion
            candidates_to_expand.append(state)

        if not candidates_to_expand:
            break

        # Expand candidates
        generated_children_for_depth: list[_PathState] = []

        for state in candidates_to_expand:
            if check_budget is not None:
                check_budget()
            total_parent_states_expanded += 1
            if metrics is not None:
                metrics["expanded_states"] = total_parent_states_expanded

            phase_started = monotonic()
            rec_result = recommend_courses(
                progress_catalog,
                eligibility_catalog,
                state.accumulated_attempts,
                reported_cumulative_gpa=reported_cumulative_gpa,
                reported_gpa_scale=reported_gpa_scale,
                reported_earned_credit_hours=reported_earned_credit_hours,
            )
            record("recommendations_ms", phase_started)

            planner_constraints = PlannerConstraints(
                max_credit_hours=constraints.max_credit_hours_per_semester,
                max_courses=constraints.max_courses_per_semester,
                max_options=semester_branch_width,
            )

            phase_started = monotonic()
            planner_result = plan_semester(
                progress_catalog,
                eligibility_catalog,
                state.accumulated_attempts,
                rec_result,
                planner_constraints,
                candidate_window_size=DEFAULT_CANDIDATE_WINDOW_SIZE,
                reported_cumulative_gpa=reported_cumulative_gpa,
                reported_gpa_scale=reported_gpa_scale,
                reported_earned_credit_hours=reported_earned_credit_hours,
                check_budget=check_budget,
                metrics=metrics,
                combination_evaluation_limit=DEFAULT_COMBINATION_EVALUATION_LIMIT,
            )
            record("semester_planner_ms", phase_started)

            # Check if Phase 8 produced zero valid combinations
            if planner_result.valid_combination_count == 0 or not planner_result.plan_options:
                # Classify termination reason when depth < max_semesters_ahead
                evidence = _collect_blocker_evidence(
                    state.academic_progress,
                    eligibility_catalog,
                    state.accumulated_attempts,
                    rec_result,
                    constraints,
                    planner_result,
                )

                # Determine PathStatus based on exact termination precedence (Priority 3, 4, 5)
                if evidence.review_required_codes and not rec_result.ranked_recommendations:
                    status = PathStatus.BLOCKED_BY_REVIEW_REQUIRED
                elif evidence.current_in_progress_codes and not rec_result.ranked_recommendations:
                    # Test whether hypothetically passing in-progress courses unlocks candidates
                    test_hyp_attempts = state.accumulated_attempts + tuple(
                        StudentCourseAttempt(c, AttemptOutcome.PASSED)
                        for c in sorted(evidence.current_in_progress_codes)
                    )
                    test_rec = recommend_courses(
                        progress_catalog,
                        eligibility_catalog,
                        test_hyp_attempts,
                        reported_cumulative_gpa=reported_cumulative_gpa,
                        reported_gpa_scale=reported_gpa_scale,
                        reported_earned_credit_hours=reported_earned_credit_hours,
                    )
                    if len(test_rec.ranked_recommendations) > 0:
                        status = PathStatus.BLOCKED_BY_CURRENT_IN_PROGRESS
                    else:
                        status = PathStatus.NO_VALID_NEXT_PLAN
                else:
                    status = PathStatus.NO_VALID_NEXT_PLAN

                finalized_states.append((state, status, evidence.diagnostic_codes))
                continue

            # Expand valid Phase 8 options into child states
            current_passed_set = _completed_passed_codes(state.academic_progress)

            for opt in planner_result.plan_options[:semester_branch_width]:
                if check_budget is not None:
                    check_budget()
                if len(opt.courses) == 0:
                    raise DegreePathIntegrityError("Child transition produces no academic-state progress")

                # Verify courses were not already passed
                for c in opt.courses:
                    if c.course_code in current_passed_set:
                        raise DegreePathIntegrityError(
                            f"Duplicate selected course '{c.course_code}' already passed"
                        )

                # Build synthetic attempts
                new_attempts = state.accumulated_attempts + tuple(
                    StudentCourseAttempt(c.course_code, AttemptOutcome.PASSED)
                    for c in opt.courses
                )

                # Recompute Phase 6
                phase_started = monotonic()
                child_progress = calculate_academic_progress(
                    progress_catalog,
                    new_attempts,
                    reported_cumulative_gpa=reported_cumulative_gpa,
                    reported_gpa_scale=reported_gpa_scale,
                    reported_earned_credit_hours=reported_earned_credit_hours,
                )
                record("child_progress_ms", phase_started)

                # Monotonicity check
                child_passed_set = _completed_passed_codes(child_progress)
                if not (child_passed_set > current_passed_set):
                    raise DegreePathIntegrityError(
                        "Monotonicity violation: child state did not strictly increase completed courses"
                    )

                # Track newly satisfied requirement groups in this semester
                parent_groups = {
                    rg.group_code: rg.is_satisfied
                    for rg in state.academic_progress.requirement_groups
                }
                newly_satisfied_sem = tuple(
                    sorted(
                        rg.group_code
                        for rg in child_progress.requirement_groups
                        if rg.is_satisfied and not parent_groups.get(rg.group_code, False)
                    )
                )

                sem_entry = ModeledSemesterEntry(
                    semester_index=state.depth + 1,
                    plan_option=opt,
                    completed_plan_credits_after=child_progress.completed_plan_credits,
                    remaining_plan_credits_after=child_progress.remaining_plan_credits,
                    newly_satisfied_requirement_group_codes=newly_satisfied_sem,
                )

                sem_codes = tuple(sorted(c.course_code for c in opt.courses))
                child_canonical_path_codes = state.canonical_path_codes + (sem_codes,)

                child_state = _PathState(
                    depth=state.depth + 1,
                    accumulated_attempts=new_attempts,
                    academic_progress=child_progress,
                    selected_semesters=state.selected_semesters + (sem_entry,),
                    unresolved_blocker_codes=(),
                    canonical_path_codes=child_canonical_path_codes,
                )

                generated_children_for_depth.append(child_state)

        if not generated_children_for_depth:
            active_beam = []
            continue

        # 6. Deduplication of Child States at Current Depth
        # Group by AcademicStateKey = (frozenset(passed), frozenset(in_progress))
        phase_started = monotonic()
        grouped_children: dict[tuple[frozenset[str], frozenset[str]], list[_PathState]] = {}
        for child in generated_children_for_depth:
            key = (
                _completed_passed_codes(child.academic_progress),
                frozenset(persisted_in_progress),
            )
            grouped_children.setdefault(key, []).append(child)

        surviving_children: list[_PathState] = []

        for key, children in grouped_children.items():
            # Check collision policy against previously seen states from shallower depths
            if key in seen_states:
                prev_depth, prev_tuple = seen_states[key]
                # If seen at a strictly shallower depth, discard deeper children
                if prev_depth < children[0].depth:
                    continue

            # Within current depth, pick best by partial priority tuple
            best_child = min(
                children,
                key=lambda c: _partial_priority_tuple(c, initial_progress),
            )
            best_tuple = _partial_priority_tuple(best_child, initial_progress)

            # If seen at equal depth, only retain if better than previously seen
            if key in seen_states:
                prev_depth, prev_tuple = seen_states[key]
                if prev_depth == best_child.depth and best_tuple >= prev_tuple:
                    continue

            seen_states[key] = (best_child.depth, best_tuple)
            surviving_children.append(best_child)

        # 7. Beam Pruning
        # Sort surviving children by partial priority tuple ascending
        surviving_children.sort(key=lambda c: _partial_priority_tuple(c, initial_progress))
        active_beam = surviving_children[:beam_width]
        record("beam_pruning_ms", phase_started)
    record("path_search_ms", search_started)

    # 8. Post-Process Finalized States into DegreePathOption instances
    phase_started = monotonic()
    if not finalized_states:
        # Fallback: initial state as no-valid-next-plan if nothing generated
        finalized_states.append((initial_state, PathStatus.NO_VALID_NEXT_PLAN, ()))

    initial_group_satisfied = {
        rg.group_code: rg.is_satisfied for rg in initial_progress.requirement_groups
    }

    raw_options: list[DegreePathOption] = []

    for state, status, blocker_codes in finalized_states:
        free_elective_requirements = _free_elective_requirements(state.academic_progress)
        if any(
            requirement.selection_state == "FREE_ELECTIVE_POLICY_REQUIRED"
            and requirement.remaining_credits_after_current > 0
            for requirement in free_elective_requirements
        ):
            blocker_codes = tuple(sorted(set(blocker_codes) | {"FREE_ELECTIVE_POLICY_REQUIRED"}))
        semester_count = len(state.selected_semesters)
        total_planned_courses = sum(
            len(s.plan_option.courses) for s in state.selected_semesters
        )
        total_planned_credits = sum(
            (s.plan_option.total_credit_hours for s in state.selected_semesters),
            Decimal("0"),
        )
        completed_plan_credit_delta = (
            state.academic_progress.completed_plan_credits
            - initial_progress.completed_plan_credits
        )
        final_completed_plan_credits = state.academic_progress.completed_plan_credits
        final_remaining_plan_credits = state.academic_progress.remaining_plan_credits

        newly_satisfied_group_codes = tuple(
            sorted(
                rg.group_code
                for rg in state.academic_progress.requirement_groups
                if rg.is_satisfied and not initial_group_satisfied.get(rg.group_code, False)
            )
        )
        newly_satisfied_group_count = len(newly_satisfied_group_codes)

        # Incomplete required courses
        unsatisfied_groups = {
            rg.group_id
            for rg in state.academic_progress.requirement_groups
            if not rg.is_satisfied
        }
        remaining_required = tuple(
            sorted(
                cp.course_code
                for cp in state.academic_progress.courses
                if cp.state is not CourseProgressState.COMPLETED
                and cp.course_code in plan_courses_by_code
                and plan_courses_by_code[cp.course_code].requirement_group_id in unsatisfied_groups
                and group_by_id[plan_courses_by_code[cp.course_code].requirement_group_id].requirement_type
                is RequirementType.REQUIRED
            )
        )

        aggregate_semester_rank_sum = sum(
            s.plan_option.rank for s in state.selected_semesters
        )

        p1 = 1 if status is PathStatus.MODELED_COMPLETE else 0
        p2 = semester_count
        p3 = completed_plan_credit_delta
        p4 = newly_satisfied_group_count
        p5 = len(blocker_codes)
        p6 = aggregate_semester_rank_sum
        p7 = state.canonical_path_codes
        selected_codes = {
            course.course_code
            for semester in state.selected_semesters
            for course in semester.plan_option.courses
        }
        unplaced_course_codes = tuple(sorted(
            set(plan_courses_by_code)
            - set(completed_course_codes)
            - set(current_course_codes)
            - selected_codes
        ))
        unplaced_credits = final_remaining_plan_credits - current_plan_credits
        if unplaced_credits < 0:
            raise DegreePathIntegrityError(
                "In-progress plan credits exceed the final remaining canonical credits"
            )
        unplaced_breakdown = _unplaced_credit_breakdown(
            state.academic_progress,
            total_unplaced_credits=unplaced_credits,
            unplaced_course_codes=unplaced_course_codes,
            blocker_codes=blocker_codes,
        )
        if sum((item.credits for item in unplaced_breakdown), Decimal("0")) != unplaced_credits:
            raise DegreePathIntegrityError(
                "Unplaced credit breakdown does not reconcile to canonical unplaced credits"
            )

        final_priority_tuple = (
            -p1,
            p2,
            -p3,
            -p4,
            p5,
            p6,
            p7,
        )

        raw_options.append(
            DegreePathOption(
                path_id=deterministic_path_id(study_plan_id, state.selected_semesters),
                rank=0,  # Assigned after sorting
                status=status,
                semesters=state.selected_semesters,
                semester_count=semester_count,
                total_planned_courses=total_planned_courses,
                total_planned_credits=total_planned_credits,
                completed_plan_credit_delta=completed_plan_credit_delta,
                final_completed_plan_credits=final_completed_plan_credits,
                final_remaining_plan_credits=final_remaining_plan_credits,
                newly_satisfied_requirement_group_count=newly_satisfied_group_count,
                newly_satisfied_requirement_group_codes=newly_satisfied_group_codes,
                remaining_required_course_codes=remaining_required,
                unresolved_blocker_codes=blocker_codes,
                aggregate_semester_rank_sum=aggregate_semester_rank_sum,
                priority_tuple=final_priority_tuple,
                reason_codes=(),  # Assigned below
                completed_course_codes=completed_course_codes,
                current_course_codes=current_course_codes,
                unplaced_course_codes=unplaced_course_codes,
                credit_summary=DegreePathCreditSummary(
                    degree_required_credits=canonical_total_credits,
                    completed_credits=initial_progress.completed_plan_credits,
                    current_credits=current_plan_credits,
                    future_placed_credits=total_planned_credits,
                    unplaced_credits=unplaced_credits,
                ),
                free_elective_requirements=free_elective_requirements,
                unplaced_credit_breakdown=unplaced_breakdown,
            )
        )

    # 9. Sort All Finalized Options Lexicographically by FinalPriorityTuple
    raw_options.sort(key=lambda opt: opt.priority_tuple)
    raw_options = deduplicate_candidate_paths(raw_options)

    # 10. Assign Relative and Absolute Reason Codes Across ALL Finalized Options
    complete_options = [opt for opt in raw_options if opt.status is PathStatus.MODELED_COMPLETE]
    min_semesters_among_complete = (
        min((opt.semester_count for opt in complete_options), default=None)
    )

    incomplete_options = [opt for opt in raw_options if opt.status is not PathStatus.MODELED_COMPLETE]
    max_progress_among_incomplete = (
        max((opt.completed_plan_credit_delta for opt in incomplete_options), default=None)
    )

    ranked_options: list[DegreePathOption] = []

    for idx, opt in enumerate(raw_options, start=1):
        reasons: list[PathReasonCode] = []

        if opt.status is PathStatus.MODELED_COMPLETE:
            reasons.append(PathReasonCode.REACHES_MODELED_PLAN_COMPLETION)
            reasons.append(PathReasonCode.COMPLETES_ALL_REQUIREMENT_GROUPS)
            if min_semesters_among_complete is not None and opt.semester_count == min_semesters_among_complete:
                reasons.append(PathReasonCode.FEWER_MODELED_SEMESTERS)
        else:
            if (
                max_progress_among_incomplete is not None
                and opt.completed_plan_credit_delta == max_progress_among_incomplete
                and max_progress_among_incomplete > Decimal("0")
            ):
                reasons.append(PathReasonCode.MAXIMIZES_PROGRESS_WITHIN_HORIZON)

        # Plan-level features across semesters
        contains_mandatory = any(
            PlanReasonCode.CONTAINS_MANDATORY_COURSES in sem.plan_option.reason_codes
            for sem in opt.semesters
        )
        if contains_mandatory:
            reasons.append(PathReasonCode.CONTAINS_MANDATORY_COURSES)

        includes_zero_cr = any(
            PlanReasonCode.INCLUDES_ZERO_CREDIT_REQUIRED in sem.plan_option.reason_codes
            for sem in opt.semesters
        )
        if includes_zero_cr:
            reasons.append(PathReasonCode.INCLUDES_ZERO_CREDIT_REQUIRED)

        previously_attempted = any(
            PlanReasonCode.INCLUDES_PREVIOUSLY_ATTEMPTED_COURSE in sem.plan_option.reason_codes
            for sem in opt.semesters
        )
        if previously_attempted:
            reasons.append(PathReasonCode.INCLUDES_PREVIOUSLY_ATTEMPTED_COURSE)

        # Terminal status specific reasons
        if opt.status is PathStatus.BLOCKED_BY_REVIEW_REQUIRED:
            reasons.append(PathReasonCode.BLOCKED_BY_REVIEW_REQUIRED)
        elif opt.status is PathStatus.BLOCKED_BY_CURRENT_IN_PROGRESS:
            reasons.append(PathReasonCode.BLOCKED_BY_CURRENT_IN_PROGRESS)
        elif opt.status is PathStatus.NO_VALID_NEXT_PLAN:
            reasons.append(PathReasonCode.NO_VALID_NEXT_SEMESTER)

        ranked_options.append(
            DegreePathOption(
                path_id=opt.path_id,
                rank=idx,
                status=opt.status,
                semesters=opt.semesters,
                semester_count=opt.semester_count,
                total_planned_courses=opt.total_planned_courses,
                total_planned_credits=opt.total_planned_credits,
                completed_plan_credit_delta=opt.completed_plan_credit_delta,
                final_completed_plan_credits=opt.final_completed_plan_credits,
                final_remaining_plan_credits=opt.final_remaining_plan_credits,
                newly_satisfied_requirement_group_count=opt.newly_satisfied_requirement_group_count,
                newly_satisfied_requirement_group_codes=opt.newly_satisfied_requirement_group_codes,
                remaining_required_course_codes=opt.remaining_required_course_codes,
                unresolved_blocker_codes=opt.unresolved_blocker_codes,
                aggregate_semester_rank_sum=opt.aggregate_semester_rank_sum,
                priority_tuple=opt.priority_tuple,
                reason_codes=tuple(reasons),
                completed_course_codes=opt.completed_course_codes,
                current_course_codes=opt.current_course_codes,
                unplaced_course_codes=opt.unplaced_course_codes,
                credit_summary=opt.credit_summary,
                free_elective_requirements=opt.free_elective_requirements,
                unplaced_credit_breakdown=opt.unplaced_credit_breakdown,
            )
        )

    # 11. Presentation Truncation (max_paths)
    final_paths = tuple(ranked_options[:constraints.max_paths])
    record("path_ranking_ms", phase_started)

    result = DegreePathResult(
        study_plan_id=study_plan_id,
        degree_path_policy_version=DEGREE_PATH_POLICY_VERSION,
        planning_scope=PLANNING_SCOPE,
        constraints=constraints,
        paths=final_paths,
        initial_completed_credits=initial_progress.completed_plan_credits,
        initial_remaining_credits=initial_progress.remaining_plan_credits,
        initial_satisfied_group_count=initial_progress.satisfied_requirement_group_count,
        total_requirement_group_count=initial_progress.total_requirement_group_count,
        unresolved_review_required_courses=unresolved_review_required,
        persisted_in_progress_courses=persisted_in_progress,
        total_parent_states_expanded=total_parent_states_expanded,
        methodology_note=_METHODOLOGY_NOTE,
        limitations=_LIMITATIONS,
    )
    phase_started = monotonic()
    validate_degree_path_result(
        progress_catalog,
        eligibility_catalog,
        student_attempts,
        result,
        reported_cumulative_gpa=reported_cumulative_gpa,
        reported_gpa_scale=reported_gpa_scale,
        reported_earned_credit_hours=reported_earned_credit_hours,
    )
    record("validation_ms", phase_started)
    return result
