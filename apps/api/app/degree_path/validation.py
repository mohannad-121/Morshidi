"""Fail-closed validation for deterministic degree-path results."""

from __future__ import annotations

from decimal import Decimal

from app.degree_path.models import (
    DegreePathResult,
    DegreePathValidationError,
    DegreePathValidationErrorCode,
    PathStatus,
    deterministic_path_id,
)
from app.progress.engine import calculate_academic_progress
from app.progress.models import AcademicProgressCatalog, CourseProgressState, RequirementType
from app.rules.evaluator import evaluate_can_take
from app.rules.models import (
    AttemptOutcome,
    CanTakeCatalog,
    CanTakeDecision,
    CanTakeRequest,
    Decision,
    StudentCourseAttempt,
)


def _fail(code: DegreePathValidationErrorCode, detail: str) -> None:
    raise DegreePathValidationError(code, detail)


def validate_degree_path_result(
    progress_catalog: AcademicProgressCatalog,
    eligibility_catalog: CanTakeCatalog,
    student_attempts: tuple[StudentCourseAttempt, ...],
    result: DegreePathResult,
    *,
    reported_cumulative_gpa: Decimal | None = None,
    reported_gpa_scale: Decimal | None = None,
    reported_earned_credit_hours: Decimal | None = None,
) -> None:
    """Recompute every path transition and reject inconsistent output.

    Elective alternatives remain accounted for as unplaced plan membership;
    only the canonical requirement-group credit target is used for graduation
    accounting, never the raw sum of every listed elective alternative.
    """
    plan_id = progress_catalog.study_plan.study_plan_id
    if result.study_plan_id != plan_id or eligibility_catalog.study_plan_id != plan_id:
        _fail(DegreePathValidationErrorCode.MISSING_PLAN_COURSE, "catalog plan ids differ")

    plan_courses = {course.course_code: course for course in progress_catalog.plan_courses}
    rule_codes = {rule.course_code for rule in eligibility_catalog.plan_courses}
    if set(plan_courses) != rule_codes:
        _fail(
            DegreePathValidationErrorCode.MISSING_PLAN_COURSE,
            "progress and prerequisite catalogs do not contain the same plan courses",
        )

    baseline = calculate_academic_progress(
        progress_catalog,
        student_attempts,
        reported_cumulative_gpa=reported_cumulative_gpa,
        reported_gpa_scale=reported_gpa_scale,
        reported_earned_credit_hours=reported_earned_credit_hours,
    )
    canonical_total = progress_catalog.study_plan.total_credit_hours
    if baseline.completed_plan_credits + baseline.remaining_plan_credits != canonical_total:
        _fail(DegreePathValidationErrorCode.CREDIT_TOTAL_MISMATCH, "baseline credits do not reconcile")
    if (
        result.initial_completed_credits != baseline.completed_plan_credits
        or result.initial_remaining_credits != baseline.remaining_plan_credits
    ):
        _fail(DegreePathValidationErrorCode.RESULT_MISMATCH, "initial progress fields differ")
    if len(result.paths) > result.constraints.max_paths:
        _fail(DegreePathValidationErrorCode.INVALID_TERM_LOAD, "too many paths returned")
    if len({path.path_id for path in result.paths}) != len(result.paths):
        _fail(DegreePathValidationErrorCode.RESULT_MISMATCH, "path ids are not unique")

    baseline_completed = {
        course.course_code
        for course in baseline.courses
        if course.state is CourseProgressState.COMPLETED
    }
    baseline_current = {
        course.course_code
        for course in baseline.courses
        if course.state is CourseProgressState.IN_PROGRESS
    }
    baseline_plan_completed = baseline_completed.intersection(plan_courses)
    baseline_plan_current = baseline_current.intersection(plan_courses)
    approved_degree_codes = baseline_completed.union(baseline_current) - set(plan_courses)
    expected_classified_codes = set(plan_courses).union(approved_degree_codes)
    group_by_id = {group.group_id: group for group in progress_catalog.requirement_groups}

    for expected_rank, path in enumerate(result.paths, start=1):
        if path.rank != expected_rank or path.semester_count != len(path.semesters):
            _fail(DegreePathValidationErrorCode.RESULT_MISMATCH, "path rank or semester count differs")
        attempts = student_attempts
        selected_codes: set[str] = set()
        raw_planned_credits = Decimal("0")
        raw_planned_courses = 0
        progress = baseline

        for semester_index, semester in enumerate(path.semesters, start=1):
            option = semester.plan_option
            if semester.semester_index != semester_index:
                _fail(DegreePathValidationErrorCode.RESULT_MISMATCH, "semester indexes are not contiguous")
            option_codes = [course.course_code for course in option.courses]
            if len(option_codes) != len(set(option_codes)) or selected_codes.intersection(option_codes):
                _fail(DegreePathValidationErrorCode.DUPLICATE_COURSE, "course appears more than once")
            if any(code not in plan_courses for code in option_codes):
                _fail(DegreePathValidationErrorCode.FOREIGN_PLAN_COURSE, "path contains a foreign course")
            if baseline_completed.intersection(option_codes):
                _fail(
                    DegreePathValidationErrorCode.COMPLETED_COURSE_REPLACED,
                    "path repeats a completed course",
                )
            if option.total_courses != len(option_codes):
                _fail(DegreePathValidationErrorCode.RESULT_MISMATCH, "semester course count differs")
            if any(
                course.credit_hours != plan_courses[course.course_code].credit_hours
                for course in option.courses
            ):
                _fail(
                    DegreePathValidationErrorCode.CREDIT_TOTAL_MISMATCH,
                    "semester course credits differ from the canonical plan",
                )

            computed_option_credits = sum(
                (plan_courses[code].credit_hours for code in option_codes), Decimal("0")
            )
            if computed_option_credits != option.total_credit_hours:
                _fail(DegreePathValidationErrorCode.CREDIT_TOTAL_MISMATCH, "semester credits differ")
            if computed_option_credits > result.constraints.max_credit_hours_per_semester:
                _fail(DegreePathValidationErrorCode.INVALID_TERM_LOAD, "semester exceeds credit limit")
            if (
                result.constraints.max_courses_per_semester is not None
                and len(option_codes) > result.constraints.max_courses_per_semester
            ):
                _fail(DegreePathValidationErrorCode.INVALID_TERM_LOAD, "semester exceeds course limit")

            for code in option_codes:
                decision = evaluate_can_take(
                    eligibility_catalog,
                    CanTakeRequest(
                        study_plan_id=plan_id,
                        target_course_code=code,
                        student_attempts=attempts,
                    ),
                )
                if not isinstance(decision, CanTakeDecision) or decision.decision is not Decision.ELIGIBLE:
                    error = (
                        DegreePathValidationErrorCode.UNRESOLVED_DEPENDENCY
                        if isinstance(decision, CanTakeDecision)
                        and decision.decision is Decision.REVIEW_REQUIRED
                        else DegreePathValidationErrorCode.PREREQUISITE_ORDER_VIOLATION
                    )
                    _fail(error, f"{code} is not eligible before semester {semester_index}")

            completed_before_semester = progress.completed_plan_credits
            attempts = attempts + tuple(
                StudentCourseAttempt(code, AttemptOutcome.PASSED) for code in option_codes
            )
            progress = calculate_academic_progress(
                progress_catalog,
                attempts,
                reported_cumulative_gpa=reported_cumulative_gpa,
                reported_gpa_scale=reported_gpa_scale,
                reported_earned_credit_hours=reported_earned_credit_hours,
            )
            if progress.completed_plan_credits + progress.remaining_plan_credits != canonical_total:
                _fail(
                    DegreePathValidationErrorCode.CREDIT_TOTAL_MISMATCH,
                    "semester credits do not reconcile",
                )
            if (
                semester.completed_plan_credits_after != progress.completed_plan_credits
                or semester.remaining_plan_credits_after != progress.remaining_plan_credits
                or option.completed_plan_credit_delta
                != progress.completed_plan_credits - completed_before_semester
            ):
                _fail(DegreePathValidationErrorCode.RESULT_MISMATCH, "semester progress fields differ")

            selected_codes.update(option_codes)
            raw_planned_credits += computed_option_credits
            raw_planned_courses += len(option_codes)

        expected_remaining_required = tuple(sorted(
            course.course_code
            for course in progress.courses
            if course.state is not CourseProgressState.COMPLETED
            and group_by_id[course.requirement_group_id].requirement_type is RequirementType.REQUIRED
            and not next(
                group.is_satisfied
                for group in progress.requirement_groups
                if group.group_id == course.requirement_group_id
            )
        ))
        if path.remaining_required_course_codes != expected_remaining_required:
            _fail(DegreePathValidationErrorCode.MISSING_PLAN_COURSE, "remaining required courses differ")

        unplaced_codes = set(plan_courses) - baseline_plan_completed - selected_codes
        accounted_codes = baseline_plan_completed | selected_codes | unplaced_codes
        if accounted_codes != set(plan_courses):
            _fail(DegreePathValidationErrorCode.MISSING_PLAN_COURSE, "not every plan course is accounted for")
        if path.total_planned_credits != raw_planned_credits or path.total_planned_courses != raw_planned_courses:
            _fail(DegreePathValidationErrorCode.CREDIT_TOTAL_MISMATCH, "path planned totals differ")
        if path.path_id != deterministic_path_id(plan_id, path.semesters):
            _fail(DegreePathValidationErrorCode.RESULT_MISMATCH, "path id differs from its allocation")
        expected_unplaced = set(plan_courses) - baseline_plan_completed - baseline_plan_current - selected_codes
        classifications = (
            set(path.completed_course_codes),
            set(path.current_course_codes),
            selected_codes,
            set(path.unplaced_course_codes),
        )
        if any(left.intersection(right) for index, left in enumerate(classifications)
               for right in classifications[index + 1:]):
            _fail(DegreePathValidationErrorCode.DUPLICATE_COURSE, "candidate classifications overlap")
        if (
            set(path.completed_course_codes) != baseline_completed
            or set(path.current_course_codes) != baseline_current
            or set(path.unplaced_course_codes) != expected_unplaced
            or set().union(*classifications) != expected_classified_codes
        ):
            _fail(DegreePathValidationErrorCode.MISSING_PLAN_COURSE, "candidate classifications differ")
        expected_free_requirements = tuple(
            (
                group.group_code,
                group.name_ar,
                group.name_en,
                group.required_credits,
                group.credited_toward_requirement,
                group.in_progress_credited_toward_requirement,
                max(
                    group.remaining_required_credits - group.in_progress_credited_toward_requirement,
                    Decimal("0"),
                ),
                group.free_elective_selection_state.value,
                tuple(sorted(
                    course.course_code for course in progress.courses
                    if course.requirement_group_id == group.group_id
                    and course.satisfies_free_elective
                    and course.state is CourseProgressState.COMPLETED
                )),
                tuple(sorted(
                    course.course_code for course in progress.courses
                    if course.requirement_group_id == group.group_id
                    and course.satisfies_free_elective
                    and course.state is CourseProgressState.IN_PROGRESS
                )),
            )
            for group in progress.requirement_groups
            if group.requirement_type is RequirementType.FREE_ELECTIVE
        )
        actual_free_requirements = tuple(
            (
                requirement.group_code,
                requirement.name_ar,
                requirement.name_en,
                requirement.required_credits,
                requirement.completed_credits,
                requirement.current_credits,
                requirement.remaining_credits_after_current,
                requirement.selection_state,
                requirement.completed_course_codes,
                requirement.current_course_codes,
            )
            for requirement in path.free_elective_requirements
        )
        if actual_free_requirements != expected_free_requirements:
            _fail(DegreePathValidationErrorCode.RESULT_MISMATCH, "free-elective requirements differ")
        expected_unplaced_credits = canonical_total - (
            baseline.completed_plan_credits
            + baseline.in_progress_plan_credits
            + raw_planned_credits
        )
        summary = path.credit_summary
        if expected_unplaced_credits < 0 or (
            summary.degree_required_credits != canonical_total
            or summary.completed_credits != baseline.completed_plan_credits
            or summary.current_credits != baseline.in_progress_plan_credits
            or summary.future_placed_credits != raw_planned_credits
            or summary.unplaced_credits != expected_unplaced_credits
            or sum((
                summary.completed_credits,
                summary.current_credits,
                summary.future_placed_credits,
                summary.unplaced_credits,
            ), Decimal("0")) != canonical_total
        ):
            _fail(DegreePathValidationErrorCode.CREDIT_TOTAL_MISMATCH, "candidate credit summary differs")
        if path.total_planned_credits != path.completed_plan_credit_delta:
            _fail(
                DegreePathValidationErrorCode.CREDIT_TOTAL_MISMATCH,
                "placed credits include courses that do not advance canonical plan credits",
            )
        if (
            path.final_completed_plan_credits != progress.completed_plan_credits
            or path.final_remaining_plan_credits != progress.remaining_plan_credits
            or path.completed_plan_credit_delta
            != progress.completed_plan_credits - baseline.completed_plan_credits
        ):
            _fail(DegreePathValidationErrorCode.CREDIT_TOTAL_MISMATCH, "path completion totals differ")
        if path.final_completed_plan_credits + path.final_remaining_plan_credits != canonical_total:
            _fail(DegreePathValidationErrorCode.CREDIT_TOTAL_MISMATCH, "final credits do not reconcile")
        if (path.status is PathStatus.MODELED_COMPLETE) != progress.all_modeled_plan_requirements_satisfied:
            _fail(DegreePathValidationErrorCode.RESULT_MISMATCH, "terminal status differs from progress")
