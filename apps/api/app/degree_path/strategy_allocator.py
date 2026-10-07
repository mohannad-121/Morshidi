"""Deterministic course allocation and sequencing for credit-timeline degree strategies.

Binds each credit-timeline scenario (e.g. FASTEST [18, 18], BALANCED [12, 12, 12])
to an exact course-by-course study plan using the deterministic recommendation
and progress projection engines.

No FastAPI, Starlette, Supabase, httpx, or LLM dependency is permitted in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from app.degree_path.credit_timeline import AcademicTerm, CreditComparisonScenario
from app.planner.models import DEFAULT_CANDIDATE_WINDOW_SIZE
from app.progress.engine import calculate_academic_progress, prepare_progress_projection
from app.progress.models import AcademicProgressCatalog
from app.recommendations.engine import recommend_courses
from app.recommendations.models import RecommendationCandidate
from app.rules.models import AttemptOutcome, CanTakeCatalog, StudentCourseAttempt

ZERO = Decimal("0")


@dataclass(frozen=True)
class StrategyCourse:
    """A single course allocated to a planned term."""

    course_code: str
    course_name_ar: str
    course_name_en: str | None
    credit_hours: Decimal
    requirement_type: str | None = None


@dataclass(frozen=True)
class StrategyTerm:
    """A single term within a strategy course plan with exact credit allocation."""

    semester_index: int
    academic_year: int
    term: AcademicTerm
    target_credit_hours: Decimal
    allocated_credit_hours: Decimal
    courses: tuple[StrategyCourse, ...]


@dataclass(frozen=True)
class StrategyDegreePath:
    """A complete, coherent course plan bound to a specific credit-timeline strategy."""

    strategy: str
    status: str  # "COMPLETE" | "PARTIAL" | "UNRESOLVABLE"
    terms: tuple[StrategyTerm, ...]
    total_target_credits: Decimal
    total_allocated_credits: Decimal
    unallocated_credit_hours: Decimal
    unresolved_course_codes: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


def allocate_strategy_degree_path(
    progress_catalog: AcademicProgressCatalog,
    eligibility_catalog: CanTakeCatalog,
    student_attempts: tuple[StudentCourseAttempt, ...],
    scenario: CreditComparisonScenario,
    *,
    reported_cumulative_gpa: Decimal | None = None,
    reported_gpa_scale: Decimal | None = None,
    reported_earned_credit_hours: Decimal | None = None,
    max_courses_per_semester: int | None = None,
    candidate_window_size: int = DEFAULT_CANDIDATE_WINDOW_SIZE,
) -> StrategyDegreePath:
    """Deterministically allocate eligible courses to match a scenario's term credit targets.

    For each term in the scenario:
    1. Precomputes eligible recommendations using current student history and synthetic passes.
    2. Explores valid course combinations within the candidate pool that do not exceed the term target.
    3. Scores combinations prioritizing exact target match, modeled progress delta, mandatory courses,
       zero-credit required courses, and recommendation rank.
    4. Simulates passing the selected courses to unlock downstream prerequisites for subsequent terms.
    """
    current_attempts = student_attempts
    planned_course_codes: set[str] = set()
    terms_result: list[StrategyTerm] = []

    names_ar: dict[str, str | None] = {
        pc.course_code: pc.course_name_ar for pc in progress_catalog.plan_courses
    }
    names_en: dict[str, str | None] = {
        rule.course_code: rule.target_name_en for rule in eligibility_catalog.plan_courses
    }

    cumulative_earned = reported_earned_credit_hours

    for term_idx, term in enumerate(scenario.timeline.terms, 1):
        target_credits = term.planned_credits
        if target_credits <= ZERO:
            terms_result.append(
                StrategyTerm(
                    semester_index=term_idx,
                    academic_year=term.academic_year,
                    term=term.term,
                    target_credit_hours=target_credits,
                    allocated_credit_hours=ZERO,
                    courses=(),
                )
            )
            continue

        rec = recommend_courses(
            progress_catalog,
            eligibility_catalog,
            current_attempts,
            reported_cumulative_gpa=reported_cumulative_gpa,
            reported_gpa_scale=reported_gpa_scale,
            reported_earned_credit_hours=cumulative_earned,
        )

        prog = calculate_academic_progress(
            progress_catalog,
            current_attempts,
            reported_cumulative_gpa=reported_cumulative_gpa,
            reported_gpa_scale=reported_gpa_scale,
            reported_earned_credit_hours=cumulative_earned,
        )
        proj = prepare_progress_projection(prog)

        candidates = [
            c for c in rec.ranked_recommendations
            if c.course_code not in planned_course_codes
        ]
        candidate_pool = candidates[:candidate_window_size]

        valid_combinations: list[tuple[RecommendationCandidate, ...]] = []

        def _dfs(index: int, current_courses: list[RecommendationCandidate], current_credits: Decimal) -> None:
            if index == len(candidate_pool):
                if current_courses:
                    valid_combinations.append(tuple(current_courses))
                return
            cand = candidate_pool[index]
            # Branch 1: include if within credit and course constraints
            if current_credits + cand.credit_hours <= target_credits:
                if max_courses_per_semester is None or len(current_courses) + 1 <= max_courses_per_semester:
                    current_courses.append(cand)
                    _dfs(index + 1, current_courses, current_credits + cand.credit_hours)
                    current_courses.pop()
            # Branch 2: exclude
            _dfs(index + 1, current_courses, current_credits)

        _dfs(0, [], ZERO)

        if not valid_combinations:
            terms_result.append(
                StrategyTerm(
                    semester_index=term_idx,
                    academic_year=term.academic_year,
                    term=term.term,
                    target_credit_hours=target_credits,
                    allocated_credit_hours=ZERO,
                    courses=(),
                )
            )
            continue

        def combination_sort_key(comb: tuple[RecommendationCandidate, ...]) -> tuple:
            tot_credits = sum((c.credit_hours for c in comb), ZERO)
            diff = abs(tot_credits - target_credits)
            codes = {c.course_code for c in comb}
            credit_delta, newly_sat = proj.selected_passes(codes)
            mand_count = sum(
                1 for c in comb
                if getattr(c.requirement_type, "value", str(c.requirement_type)) == "required"
            )
            zero_cr_mand = sum(
                1 for c in comb
                if c.credit_hours == ZERO and getattr(c.requirement_type, "value", str(c.requirement_type)) == "required"
            )
            rank_sum = sum(c.rank for c in comb)
            canonical_codes = tuple(sorted(c.course_code for c in comb))
            return (
                diff,              # 1. Closest match to target credit hours (0 is exact)
                -credit_delta,     # 2. Maximum modeled credit contribution
                -mand_count,       # 3. Maximum mandatory courses
                -zero_cr_mand,     # 4. Include zero-credit required courses
                -len(newly_sat),   # 5. Maximum requirement groups satisfied
                -tot_credits,      # 6. Maximum credits up to target
                rank_sum,          # 7. Lowest recommendation rank sum
                canonical_codes,   # 8. Deterministic tie-breaker
            )

        best = min(valid_combinations, key=combination_sort_key)
        tot_best = sum((c.credit_hours for c in best), ZERO)

        term_courses: list[StrategyCourse] = []
        for c in best:
            term_courses.append(
                StrategyCourse(
                    course_code=c.course_code,
                    course_name_ar=names_ar.get(c.course_code) or c.course_name_ar or c.course_code,
                    course_name_en=names_en.get(c.course_code),
                    credit_hours=c.credit_hours,
                    requirement_type=getattr(c.requirement_type, "value", str(c.requirement_type)),
                )
            )
            planned_course_codes.add(c.course_code)

        terms_result.append(
            StrategyTerm(
                semester_index=term_idx,
                academic_year=term.academic_year,
                term=term.term,
                target_credit_hours=target_credits,
                allocated_credit_hours=tot_best,
                courses=tuple(term_courses),
            )
        )

        new_synthetic_attempts = tuple(
            StudentCourseAttempt(course_code=c.course_code, outcome=AttemptOutcome.PASSED)
            for c in best
        )
        current_attempts = current_attempts + new_synthetic_attempts
        if cumulative_earned is not None:
            cumulative_earned += tot_best

    total_target = sum((t.target_credit_hours for t in terms_result), ZERO)
    total_allocated = sum((t.allocated_credit_hours for t in terms_result), ZERO)
    unallocated = max(ZERO, total_target - total_allocated)

    if unallocated == ZERO and total_allocated > ZERO:
        status = "COMPLETE"
    elif total_allocated > ZERO:
        status = "PARTIAL"
    else:
        status = "UNRESOLVABLE"

    limitations: list[str] = [
        "توزيع المقررات يعتمد على المتطلبات السابقة وشروط فتح المواد الحالية في نموذج الخطة.",
        "النجاح الفعلي وتوفر الشعب في الفصول القادمة قد يتطلب إعادة موازنة المسار.",
    ]
    if status == "PARTIAL":
        limitations.append(
            f"تعذر توزيع {unallocated} ساعة ضمن الحدود الأكاديمية وشبكة المتطلبات الحالية."
        )

    return StrategyDegreePath(
        strategy=scenario.mode.value if hasattr(scenario.mode, "value") else str(scenario.mode),
        status=status,
        terms=tuple(terms_result),
        total_target_credits=total_target,
        total_allocated_credits=total_allocated,
        unallocated_credit_hours=unallocated,
        unresolved_course_codes=(),
        limitations=tuple(limitations),
    )

