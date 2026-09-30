"""Ownership-safe orchestration for self-service student operations."""

import asyncio
from decimal import Decimal
import logging
from threading import Event
from time import monotonic, perf_counter
from typing import Any, Awaitable, Callable
from uuid import UUID

from app.degree_path.engine import plan_degree_paths
from app.degree_path.models import (
    DegreePathCapacityError,
    DegreePathComputationTimeout,
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
from app.rules.models import AttemptOutcome, CanTakeCatalog
from app.catalog.repository import AcademicCatalogRepository
from app.catalog.roadmap_metadata import RoadmapPlanMetadata
from app.advisor.models import ResolvedCourseReference
from app.core.request_timing import request_id_context
from app.core.academic_compute import AcademicComputeLimiter
from app.progress.engine import calculate_academic_progress
from app.progress.models import AcademicProgress, AcademicProgressCatalog
from app.recommendations.engine import recommend_courses
from app.recommendations.models import RecommendationResult
from app.roadmap.engine import AcademicRoadmap, build_roadmap, overlay_from_degree_path
from app.roadmap.fingerprint import academic_input_fingerprint
from app.roadmap.report import ModeledAcademicReport, build_report_snapshot
from app.services.eligibility import EligibilityService
from app.student.errors import StudentAttemptNotFound, StudentProfileValidationError
from app.student.models import StudentAcademicState, StudentCourseAttemptRecord
from app.student.supabase_repository import SupabaseStudentAcademicRepository


class StudentConfigurationError(RuntimeError):
    """The server-side student repository has not been configured."""


DEGREE_PATH_BUDGET_SECONDS = 50.0
logger = logging.getLogger("uvicorn.error")


class StudentService:
    def __init__(
        self,
        repository: SupabaseStudentAcademicRepository,
        eligibility: EligibilityService,
        catalog_repository: AcademicCatalogRepository,
        academic_compute_limiter: AcademicComputeLimiter | None = None,
    ) -> None:
        self._repository = repository
        self._eligibility = eligibility
        self._catalog_repository = catalog_repository
        self._academic_compute_limiter = academic_compute_limiter or AcademicComputeLimiter()

    async def get_profile(self, owner: str) -> StudentAcademicState:
        return await self._repository.load_student_academic_state(owner)

    async def resolve_student_university_id(self, owner: str) -> str:
        """Resolve the authenticated owner's university through the existing repository boundary."""
        return await self._repository.resolve_student_university_id(owner)

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

        return await self._academic_compute_limiter.run(
            lambda check_budget: plan_semester(
                progress_catalog,
                eligibility_catalog,
                state.attempts,
                full_recommendations,
                constraints,
                candidate_window_size=candidate_window_size,
                reported_cumulative_gpa=state.reported_cumulative_gpa,
                reported_gpa_scale=state.reported_gpa_scale,
                reported_earned_credit_hours=state.reported_earned_credit_hours,
                check_budget=check_budget,
            ),
        )

    async def get_academic_roadmap(self, owner: str) -> AcademicRoadmap:
        """One owner lookup, four plan-scoped catalog reads, no degree-path search."""
        state = await self.get_profile(owner)
        progress, eligibility, names, metadata = await asyncio.gather(
            self._catalog_repository.load_progress_catalog(state.study_plan_id),
            self._catalog_repository.load_plan_eligibility_catalog(state.study_plan_id),
            self._catalog_repository.load_advisor_course_catalog(state.study_plan_id),
            self._catalog_repository.load_roadmap_plan_metadata(state.study_plan_id),
        )
        return build_roadmap(progress, eligibility, names, state.attempts, plan_metadata=metadata)

    async def get_academic_report(self, owner: str) -> ModeledAcademicReport:
        """Freeze one owner-scoped roadmap projection for screen and print."""
        return build_report_snapshot(await self.get_academic_roadmap(owner))

    async def get_modeled_roadmap(
        self,
        owner: str,
        *,
        max_credit_hours_per_semester: Decimal,
        max_courses_per_semester: int | None = None,
        max_semesters_ahead: int = 8,
        max_paths: int = 1,
        cancel_event: Event | None = None,
    ) -> AcademicRoadmap:
        """Explicit bounded degree path + roadmap from the same owner/catalog inputs."""
        captured: tuple[StudentAcademicState, AcademicProgressCatalog, CanTakeCatalog,
                        tuple[ResolvedCourseReference, ...], RoadmapPlanMetadata] | None = None

        async def capture(state: StudentAcademicState, progress: AcademicProgressCatalog,
                          eligibility: CanTakeCatalog) -> None:
            nonlocal captured
            names, metadata = await asyncio.gather(
                self._catalog_repository.load_advisor_course_catalog(state.study_plan_id),
                self._catalog_repository.load_roadmap_plan_metadata(state.study_plan_id),
            )
            captured = (state, progress, eligibility, names, metadata)

        result = await self.get_degree_paths(
            owner,
            max_credit_hours_per_semester=max_credit_hours_per_semester,
            max_courses_per_semester=max_courses_per_semester,
            max_semesters_ahead=max_semesters_ahead,
            max_paths=max_paths,
            cancel_event=cancel_event,
            snapshot_callback=capture,
        )
        if captured is None:
            raise StudentConfigurationError("Modeled roadmap input snapshot was not captured")
        state, progress, eligibility, names, metadata = captured
        fingerprint = academic_input_fingerprint(progress, eligibility, names, state.attempts, metadata)
        overlay = overlay_from_degree_path(result, fingerprint)
        return build_roadmap(progress, eligibility, names, state.attempts,
                             plan_metadata=metadata, modeled_overlay=overlay)

    async def get_degree_paths(
        self,
        owner: str,
        *,
        max_credit_hours_per_semester: Decimal,
        max_courses_per_semester: int | None = None,
        max_semesters_ahead: int = 8,
        max_paths: int = 3,
        cancel_event: Event | None = None,
        snapshot_callback: Callable[[StudentAcademicState, AcademicProgressCatalog, CanTakeCatalog], Awaitable[None]] | None = None,
    ) -> DegreePathResult:
        """Deterministically generate multi-semester degree paths for the authenticated student.

        Loads student academic state once, loads progress and eligibility catalogs once,
        constructs DegreePathConstraints from user parameters, and invokes the pure engine.
        Internal engine parameters (beam_width, semester_branch_width) remain engine defaults.
        """
        started = perf_counter()
        deadline = monotonic() + DEGREE_PATH_BUDGET_SECONDS
        cancellation = cancel_event or Event()
        metrics: dict[str, float | int] = {}
        def calculate(progress_catalog, eligibility_catalog, state, constraints, check_budget):
            engine_started = perf_counter()
            try:
                return plan_degree_paths(
                    progress_catalog,
                    eligibility_catalog,
                    state.attempts,
                    constraints,
                    reported_cumulative_gpa=state.reported_cumulative_gpa,
                    reported_gpa_scale=state.reported_gpa_scale,
                    reported_earned_credit_hours=state.reported_earned_credit_hours,
                    check_budget=check_budget,
                    metrics=metrics,
                )
            finally:
                metrics["engine_ms"] = (perf_counter() - engine_started) * 1000
                for phase, value in sorted(metrics.items()):
                    logger.info(
                        "degree_path_phase request_id=%s phase=%s value=%.1f",
                        request_id_context.get(), phase, value,
                    )

        try:
            async with asyncio.timeout(DEGREE_PATH_BUDGET_SECONDS):
                phase_started = perf_counter()
                state = await self.get_profile(owner)
                metrics["student_resolution_ms"] = (perf_counter() - phase_started) * 1000
                logger.info(
                    "degree_path_phase request_id=%s phase=student_resolution_ms value=%.1f",
                    request_id_context.get(), metrics["student_resolution_ms"],
                )

                async def timed_catalog(load):
                    catalog_started = perf_counter()
                    value = await load(state.study_plan_id)
                    return value, (perf_counter() - catalog_started) * 1000

                (progress_catalog, progress_ms), (eligibility_catalog, eligibility_ms) = await asyncio.gather(
                    timed_catalog(self._catalog_repository.load_progress_catalog),
                    timed_catalog(self._catalog_repository.load_plan_eligibility_catalog),
                )
                metrics["progress_catalog_ms"] = progress_ms
                metrics["eligibility_catalog_ms"] = eligibility_ms
                if snapshot_callback is not None:
                    await snapshot_callback(state, progress_catalog, eligibility_catalog)
                logger.info(
                    "degree_path_phase request_id=%s phase=progress_catalog_ms value=%.1f",
                    request_id_context.get(), progress_ms,
                )
                logger.info(
                    "degree_path_phase request_id=%s phase=eligibility_catalog_ms value=%.1f",
                    request_id_context.get(), eligibility_ms,
                )
                constraints = DegreePathConstraints(
                    max_credit_hours_per_semester=max_credit_hours_per_semester,
                    max_courses_per_semester=max_courses_per_semester,
                    max_semesters_ahead=max_semesters_ahead,
                    max_paths=max_paths,
                )
                result = await self._academic_compute_limiter.run(
                    lambda check_budget: calculate(
                        progress_catalog, eligibility_catalog, state, constraints, check_budget,
                    ),
                    deadline=deadline,
                    cancel_event=cancellation,
                )
                logger.info(
                    "degree_path_timing request_id=%s total_service_ms=%.1f",
                    request_id_context.get(), (perf_counter() - started) * 1000,
                )
                return result
        except TimeoutError as error:
            cancellation.set()
            raise DegreePathComputationTimeout("Degree path computation budget expired") from error
        except asyncio.CancelledError:
            cancellation.set()
            raise
