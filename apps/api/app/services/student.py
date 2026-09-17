"""Ownership-safe orchestration for self-service student operations."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.degree_path.engine import plan_degree_paths
from app.degree_path.models import (
    DegreePathConstraints,
    DegreePathResult,
)
from app.planner.engine import plan_semester
from app.planner.models import (
    DEFAULT_CANDIDATE_WINDOW_SIZE,
    PlannerConstraints,
    SemesterPlannerResult,
)
from app.rules.evaluator import CanTakeResult
from app.rules.models import AttemptOutcome
from app.catalog.repository import AcademicCatalogRepository
from app.progress.engine import calculate_academic_progress
from app.progress.models import AcademicProgress
from app.recommendations.engine import recommend_courses
from app.recommendations.models import RecommendationResult
from app.services.eligibility import EligibilityService
from app.student.errors import StudentAttemptNotFound, StudentProfileValidationError
from app.student.models import StudentAcademicState, StudentCourseAttemptRecord
from app.student.supabase_repository import SupabaseStudentAcademicRepository


class StudentConfigurationError(RuntimeError):
    """The server-side student repository has not been configured."""


class StudentService:
    def __init__(
        self,
        repository: SupabaseStudentAcademicRepository,
        eligibility: EligibilityService,
        catalog_repository: AcademicCatalogRepository,
    ) -> None:
        self._repository = repository
        self._eligibility = eligibility
        self._catalog_repository = catalog_repository

    async def get_profile(self, owner: str) -> StudentAcademicState:
        return await self._repository.load_student_academic_state(owner)

    async def create_profile(self, owner: str, **values: Any) -> StudentAcademicState:
        return await self._repository.create_profile(owner, **values)

    async def update_profile(self, owner: str, changes: dict[str, Any]) -> StudentAcademicState:
        current = await self.get_profile(owner)
        merged = {"reported_cumulative_gpa": current.reported_cumulative_gpa,
            "reported_gpa_scale": current.reported_gpa_scale,
            "reported_earned_credit_hours": current.reported_earned_credit_hours, **changes}
        if (merged["reported_cumulative_gpa"] is None) != (merged["reported_gpa_scale"] is None):
            raise StudentProfileValidationError("Reported GPA and scale must be supplied together")
        return await self._repository.update_profile(owner, **merged)

    async def delete_profile(self, owner: str) -> None:
        await self._repository.delete_profile(owner)

    async def list_attempts(self, owner: str) -> tuple[StudentCourseAttemptRecord, ...]:
        return await self._repository.load_attempt_records(owner)

    async def create_attempt(self, owner: str, course_code: str, status: AttemptOutcome, **values: Any) -> StudentCourseAttemptRecord:
        return await self._repository.create_attempt(owner, course_code, status, **values)

    async def update_attempt(self, owner: str, attempt_id: UUID, changes: dict[str, Any]) -> StudentCourseAttemptRecord:
        current = next((row for row in await self.list_attempts(owner) if row.attempt_id == str(attempt_id)), None)
        if current is None:
            raise StudentAttemptNotFound("Student course attempt was not found")
        merged = {"outcome": current.outcome, "attempt_sequence": current.attempt_sequence,
            "term_label": current.term_label, "attempted_on": current.attempted_on,
            "reported_grade_text": current.reported_grade_text, "record_source": current.record_source}
        changes = dict(changes)
        if "status" in changes: changes["outcome"] = changes.pop("status")
        if "raw_grade_text" in changes: changes["reported_grade_text"] = changes.pop("raw_grade_text")
        merged.update(changes)
        return await self._repository.update_attempt(owner, attempt_id, **merged)

    async def delete_attempt(self, owner: str, attempt_id: UUID) -> None:
        await self._repository.delete_attempt(owner, attempt_id)

    async def evaluate_can_take(self, owner: str, target_course_code: str) -> CanTakeResult:
        state = await self.get_profile(owner)
        return await self._eligibility.evaluate_can_take(UUID(state.study_plan_id), target_course_code, state.attempts)

    async def get_academic_progress(self, owner: str) -> AcademicProgress:
        state = await self.get_profile(owner)
        catalog = await self._catalog_repository.load_progress_catalog(state.study_plan_id)
        return calculate_academic_progress(
            catalog,
            state.attempts,
            reported_cumulative_gpa=state.reported_cumulative_gpa,
            reported_gpa_scale=state.reported_gpa_scale,
            reported_earned_credit_hours=state.reported_earned_credit_hours,
        )

    async def get_course_recommendations(
        self,
        owner: str,
        *,
        limit: int | None = None,
    ) -> RecommendationResult:
        if limit is not None and limit < 1:
            raise ValueError("limit must be greater than or equal to 1")
        state = await self.get_profile(owner)
        progress_catalog = await self._catalog_repository.load_progress_catalog(state.study_plan_id)
        eligibility_catalog = await self._catalog_repository.load_plan_eligibility_catalog(state.study_plan_id)
        result = recommend_courses(
            progress_catalog,
            eligibility_catalog,
            state.attempts,
            reported_cumulative_gpa=state.reported_cumulative_gpa,
            reported_gpa_scale=state.reported_gpa_scale,
            reported_earned_credit_hours=state.reported_earned_credit_hours,
        )
        if limit is not None:
            result = RecommendationResult(
                study_plan_id=result.study_plan_id,
                recommendation_policy_version=result.recommendation_policy_version,
                ranked_recommendations=result.ranked_recommendations[:limit],
                review_required_courses=result.review_required_courses,
                excluded_in_progress=result.excluded_in_progress,
                methodology_note=result.methodology_note,
                limitations=result.limitations,
            )
        return result

    async def get_semester_plans(
        self,
        owner: str,
        *,
        max_credit_hours: Decimal,
        max_courses: int | None = None,
        max_options: int = 5,
        candidate_window_size: int = DEFAULT_CANDIDATE_WINDOW_SIZE,
    ) -> SemesterPlannerResult:
        """Deterministically generate optimal semester plans for the authenticated student.

        Loads student academic state once, loads progress and eligibility catalogs once,
        computes full Phase 7 recommendation candidates without presentation limits,
        and invokes the pure planner engine.
        """
        state = await self.get_profile(owner)
        progress_catalog = await self._catalog_repository.load_progress_catalog(state.study_plan_id)
        eligibility_catalog = await self._catalog_repository.load_plan_eligibility_catalog(state.study_plan_id)

        # Compute full Phase 7 recommendations without any presentation limit
        full_recommendations = recommend_courses(
            progress_catalog,
            eligibility_catalog,
            state.attempts,
            reported_cumulative_gpa=state.reported_cumulative_gpa,
            reported_gpa_scale=state.reported_gpa_scale,
            reported_earned_credit_hours=state.reported_earned_credit_hours,
        )

        constraints = PlannerConstraints(
            max_credit_hours=max_credit_hours,
            max_courses=max_courses,
            max_options=max_options,
        )

        return plan_semester(
            progress_catalog,
            eligibility_catalog,
            state.attempts,
            full_recommendations,
            constraints,
            candidate_window_size=candidate_window_size,
            reported_cumulative_gpa=state.reported_cumulative_gpa,
            reported_gpa_scale=state.reported_gpa_scale,
            reported_earned_credit_hours=state.reported_earned_credit_hours,
        )

    async def get_degree_paths(
        self,
        owner: str,
        *,
        max_credit_hours_per_semester: Decimal,
        max_courses_per_semester: int | None = None,
        max_semesters_ahead: int = 8,
        max_paths: int = 3,
    ) -> DegreePathResult:
        """Deterministically generate multi-semester degree paths for the authenticated student.

        Loads student academic state once, loads progress and eligibility catalogs once,
        constructs DegreePathConstraints from user parameters, and invokes the pure engine.
        Internal engine parameters (beam_width, semester_branch_width) remain engine defaults.
        """
        state = await self.get_profile(owner)
        progress_catalog = await self._catalog_repository.load_progress_catalog(state.study_plan_id)
        eligibility_catalog = await self._catalog_repository.load_plan_eligibility_catalog(state.study_plan_id)

        constraints = DegreePathConstraints(
            max_credit_hours_per_semester=max_credit_hours_per_semester,
            max_courses_per_semester=max_courses_per_semester,
            max_semesters_ahead=max_semesters_ahead,
            max_paths=max_paths,
        )

        return plan_degree_paths(
            progress_catalog,
            eligibility_catalog,
            state.attempts,
            constraints,
            reported_cumulative_gpa=state.reported_cumulative_gpa,
            reported_gpa_scale=state.reported_gpa_scale,
            reported_earned_credit_hours=state.reported_earned_credit_hours,
        )
