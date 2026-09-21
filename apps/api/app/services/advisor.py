"""Authenticated, read-only coordination for the advisor boundary."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from app.advisor.explanation import (
    AdvisorExplanationProvider,
    ExplanationFailure,
    ExplanationLanguage,
    ExplanationStatus,
    build_explanation_input,
    deterministic_explanation,
    explanation_passes_guards,
    invoke_explanation_provider,
)
from app.advisor.interpretation import (
    InterpretationStatus,
    invoke_advisor_provider_async,
    normalize_advisor_interpretation,
)
from app.advisor.models import (
    AdvisorIntent,
    EntityResolutionStatus,
    StructuredAdvisorResult,
)
from app.advisor.orchestrator import AdvisorContext, orchestrate_advisor_request
from app.advisor.provider import AdvisorLLMProvider, ProviderFailure, RawAdvisorInterpretation
from app.catalog.repository import AcademicCatalogRepository
from app.student.models import StudentAcademicState
from app.student.repository import StudentAcademicRepository


class AdvisorConfigurationError(RuntimeError):
    """The server-side advisor service has not been configured."""


class AdvisorProviderError(RuntimeError):
    """A typed provider-boundary failure that contains no provider payload."""

    def __init__(self, failure: ProviderFailure) -> None:
        super().__init__(failure.message_key)
        self.failure = failure


@dataclass(frozen=True)
class AdvisorServiceResult:
    structured_result: StructuredAdvisorResult
    explanation: str | None
    explanation_status: ExplanationStatus
    explanation_language: ExplanationLanguage | None


logger = logging.getLogger(__name__)


class AdvisorService:
    """Load only authoritative data needed by one interpreted advisor intent."""

    def __init__(
        self,
        student_repository: StudentAcademicRepository,
        catalog_repository: AcademicCatalogRepository,
        provider: AdvisorLLMProvider,
        explanation_provider: AdvisorExplanationProvider | None = None,
    ) -> None:
        self._student_repository = student_repository
        self._catalog_repository = catalog_repository
        self._provider = provider
        self._explanation_provider = explanation_provider

    async def advise(self, owner_user_id: str, message: str) -> StructuredAdvisorResult:
        """Interpret once, load server-owned context in batches, and orchestrate."""

        provider_output = await invoke_advisor_provider_async(self._provider, message)
        if isinstance(provider_output, ProviderFailure):
            raise AdvisorProviderError(provider_output)
        assert isinstance(provider_output, RawAdvisorInterpretation)

        state: StudentAcademicState | None = None
        resolution_catalog = ()
        if _needs_course_catalog(provider_output):
            state = await self._student_repository.load_student_academic_state(owner_user_id)
            resolution_catalog = await self._catalog_repository.load_advisor_course_catalog(
                state.study_plan_id
            )

        interpretation = normalize_advisor_interpretation(
            message,
            provider_output,
            resolution_catalog,
        )
        if interpretation.status is InterpretationStatus.INTERPRETATION_FAILED:
            assert interpretation.failure is not None
            raise AdvisorProviderError(interpretation.failure)
        request = interpretation.normalized_request
        assert request is not None

        if request.intent in (
            AdvisorIntent.GENERAL_ACADEMIC_INFORMATION,
            AdvisorIntent.CLARIFICATION_REQUIRED,
            AdvisorIntent.OUT_OF_SCOPE,
            AdvisorIntent.OPTION_COMPARISON,
        ):
            return orchestrate_advisor_request(request, AdvisorContext())
        if (
            request.course_resolution is not None
            and request.course_resolution.status is EntityResolutionStatus.NOT_FOUND
        ):
            return orchestrate_advisor_request(request, AdvisorContext())

        if state is None:
            state = await self._student_repository.load_student_academic_state(owner_user_id)

        progress_catalog = None
        eligibility_catalog = None
        if request.intent in (
            AdvisorIntent.ACADEMIC_STATUS,
            AdvisorIntent.REMAINING_REQUIREMENTS,
            AdvisorIntent.COURSE_RECOMMENDATIONS,
            AdvisorIntent.SEMESTER_PLANNING,
            AdvisorIntent.DEGREE_PATH_MODELING,
            AdvisorIntent.COURSE_INFORMATION,
        ):
            progress_catalog = await self._catalog_repository.load_progress_catalog(
                state.study_plan_id
            )
        if request.intent in (
            AdvisorIntent.COURSE_ELIGIBILITY,
            AdvisorIntent.COURSE_RECOMMENDATIONS,
            AdvisorIntent.SEMESTER_PLANNING,
            AdvisorIntent.DEGREE_PATH_MODELING,
            AdvisorIntent.COURSE_INFORMATION,
        ):
            eligibility_catalog = await self._catalog_repository.load_plan_eligibility_catalog(
                state.study_plan_id
            )

        context = AdvisorContext(
            progress_catalog=progress_catalog,
            eligibility_catalog=eligibility_catalog,
            student_attempts=state.attempts,
            reported_cumulative_gpa=state.reported_cumulative_gpa,
            reported_gpa_scale=state.reported_gpa_scale,
            reported_earned_credit_hours=state.reported_earned_credit_hours,
        )
        return orchestrate_advisor_request(request, context)

    async def advise_with_explanation(
        self,
        owner_user_id: str,
        message: str,
    ) -> AdvisorServiceResult:
        """Add presentational prose after orchestration without changing its result."""

        structured = await self.advise(owner_user_id, message)
        template = deterministic_explanation(message, structured)
        if template is not None:
            return AdvisorServiceResult(
                structured,
                template.text,
                ExplanationStatus.NOT_REQUIRED,
                template.language,
            )
        if self._explanation_provider is None:
            return AdvisorServiceResult(
                structured,
                None,
                ExplanationStatus.UNAVAILABLE,
                None,
            )
        explanation_input = build_explanation_input(message, structured)
        response = await invoke_explanation_provider(
            self._explanation_provider,
            explanation_input,
        )
        if isinstance(response, ExplanationFailure):
            logger.warning("advisor explanation failed")
            return AdvisorServiceResult(
                structured,
                None,
                ExplanationStatus.UNAVAILABLE,
                None,
            )
        if not explanation_passes_guards(explanation_input, structured, response):
            logger.warning("advisor explanation rejected by grounding guard")
            return AdvisorServiceResult(
                structured,
                None,
                ExplanationStatus.REJECTED_BY_GUARD,
                None,
            )
        return AdvisorServiceResult(
            structured,
            response.text,
            ExplanationStatus.GENERATED,
            response.language,
        )


def _needs_course_catalog(raw: RawAdvisorInterpretation) -> bool:
    return (
        raw.intent in (
            AdvisorIntent.COURSE_ELIGIBILITY.value,
            AdvisorIntent.COURSE_INFORMATION.value,
        )
        and bool(raw.course_mentions or raw.course_codes_mentioned)
    )
