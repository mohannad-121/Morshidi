from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.eligibility import router as eligibility_router
from app.api.routes.health import router as health_router
from app.api.routes.student import router as student_router
from app.api.routes.advisor import router as advisor_router
from app.api.routes.mock_registration import router as mock_registration_router
from app.api.routes.institutional_demand import router as institutional_demand_router
from app.api.routes.institutional_intelligence import router as institutional_intelligence_router
from app.institutional_intelligence_service import (
    HTTP_STATUS as INSTITUTIONAL_INTELLIGENCE_HTTP_STATUS,
    InstitutionalIntelligenceService,
    InstitutionalIntelligenceServiceError,
)
from app.advisor.provider import ProviderFailureType, UnconfiguredAdvisorLLMProvider
from app.providers.advisor_openai import OpenAIAdvisorProvider
from app.catalog.errors import (
    CatalogIntegrityError,
    CatalogTransportError,
    StudyPlanNotFound,
    TargetCourseNotFound,
    TargetCourseNotInStudyPlan,
)
from app.catalog.supabase_repository import SupabaseAcademicCatalogRepository
from app.core.config import settings
from app.services.eligibility import EligibilityConfigurationError, EligibilityService
from app.services.student import StudentConfigurationError, StudentService
from app.services.advisor import (
    AdvisorConfigurationError,
    AdvisorProviderError,
    AdvisorService,
)
from app.student.errors import (
    StudentAttemptNotFound, StudentCourseNotFound, StudentCourseUniversityMismatch,
    StudentProfileAlreadyExists, StudentProfileIntegrityError, StudentProfileNotFound,
    StudentProfileTransportError, StudentProfileValidationError, StudentStudyPlanNotFound,
)
from app.student.supabase_repository import SupabaseStudentAcademicRepository
from app.progress.models import ProgressIntegrityError
from app.planner.models import PlannerIntegrityError
from app.degree_path.models import (
    DegreePathConstraintError,
    DegreePathIntegrityError,
)
from app.mock_registration_persistence.repository import SupabaseMockRegistrationRepository
from app.mock_registration_service.context import SupabaseAcademicContextLoader
from app.mock_registration_service.errors import (
    HTTP_STATUS, MockRegistrationServiceError, ServiceErrorCode,
)
from app.mock_registration_service.institutional_service import InstitutionalDemandService
from app.mock_registration_service.student_service import MockRegistrationStudentService


def build_advisor_providers(client: httpx.AsyncClient):
    """Select the concrete adapter only from complete server-side configuration."""

    if (
        settings.advisor_llm_api_key is not None
        and settings.advisor_llm_api_key.get_secret_value().strip()
        and settings.advisor_llm_model is not None
        and settings.advisor_llm_model.strip()
    ):
        provider = OpenAIAdvisorProvider(
            settings.advisor_llm_api_key.get_secret_value(),
            settings.advisor_llm_model,
            client,
        )
        return provider, provider
    return UnconfiguredAdvisorLLMProvider(), None


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Own one reusable server-side Data API client for the application lifetime."""

    client = httpx.AsyncClient()
    application.state.catalog_http_client = client
    application.state.auth_http_client = client
    application.state.eligibility_service = None
    application.state.student_service = None
    application.state.advisor_service = None
    application.state.mock_registration_student_service = None
    application.state.institutional_demand_service = None
    application.state.institutional_intelligence_service = None
    if settings.supabase_url and settings.supabase_secret_key:
        repository = SupabaseAcademicCatalogRepository(
            settings.supabase_url,
            settings.supabase_secret_key.get_secret_value(),
            client,
        )
        application.state.eligibility_service = EligibilityService(repository)
        student_repository = SupabaseStudentAcademicRepository(
            settings.supabase_url,
            settings.supabase_secret_key.get_secret_value(),
            client,
        )
        application.state.student_service = StudentService(
            student_repository,
            application.state.eligibility_service,
            repository,
        )
        advisor_provider, explanation_provider = build_advisor_providers(client)
        application.state.advisor_service = AdvisorService(
            student_repository,
            repository,
            advisor_provider,
            explanation_provider,
        )
        persistence = SupabaseMockRegistrationRepository(
            settings.supabase_url, settings.supabase_secret_key.get_secret_value(), client)
        context_loader = SupabaseAcademicContextLoader(
            settings.supabase_url, settings.supabase_secret_key.get_secret_value(), client,
            student_repository, repository)
        application.state.mock_registration_student_service = MockRegistrationStudentService(
            persistence, context_loader)
        privacy_fields = {
            "mock_registration_minimum_disclosure_group_size",
            "mock_registration_max_intents",
            "mock_registration_max_catalog_courses",
        }
        if settings.app_env in {"development", "test"} or privacy_fields <= settings.model_fields_set:
            application.state.institutional_demand_service = InstitutionalDemandService(
                persistence, context_loader,
                minimum_disclosure_group_size=settings.mock_registration_minimum_disclosure_group_size,
                max_intents=settings.mock_registration_max_intents,
                max_catalog_courses=settings.mock_registration_max_catalog_courses,
            )
            application.state.institutional_intelligence_service = InstitutionalIntelligenceService(
                persistence,
                context_loader,
                repository,
                application.state.institutional_demand_service,
            )
    try:
        yield
    finally:
        await client.aclose()


app = FastAPI(
    title=settings.app_name,
    description="Academic intelligence backend for Morshidi.",
    version=settings.app_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(eligibility_router)
app.include_router(student_router)
app.include_router(advisor_router)
app.include_router(mock_registration_router)
app.include_router(institutional_demand_router)
app.include_router(institutional_intelligence_router)


def _catalog_error_response(error_code: str, detail: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"kind": "error", "error_code": error_code, "detail": detail},
    )


@app.exception_handler(MockRegistrationServiceError)
async def handle_mock_registration_service_error(
    _: Request, exc: MockRegistrationServiceError
) -> JSONResponse:
    messages = {
        ServiceErrorCode.AUTH_REQUIRED: "Authentication is required",
        ServiceErrorCode.OWNER_SCOPE_MISMATCH: "Requested resource was not found",
        ServiceErrorCode.ACADEMIC_CONTEXT_UNAVAILABLE: "Academic context is unavailable",
        ServiceErrorCode.ACADEMIC_STATE_CHANGED: "Academic information changed; refresh and retry",
        ServiceErrorCode.INVALID_INTENT: "Mock Registration intent is invalid",
        ServiceErrorCode.REVIEW_REQUIRED: "Academic review is required",
        ServiceErrorCode.REVISION_CONFLICT: "Mock Registration intent changed; refresh and retry",
        ServiceErrorCode.PERIOD_INVALID: "Target period is unavailable",
        ServiceErrorCode.PLAN_SCOPE_INVALID: "Academic plan context is invalid",
        ServiceErrorCode.PERSISTENCE_CONFLICT: "Mock Registration state changed; refresh and retry",
        ServiceErrorCode.PERSISTENCE_UNAVAILABLE: "Mock Registration storage is unavailable",
        ServiceErrorCode.INSTITUTIONAL_ACCESS_DENIED: "Institutional demand access is denied",
        ServiceErrorCode.AGGREGATION_SCOPE_INVALID: "Institutional demand scope is invalid",
        ServiceErrorCode.RESOURCE_NOT_FOUND: "Requested resource was not found",
    }
    return JSONResponse(status_code=HTTP_STATUS[exc.code], content={
        "kind": "error", "error_code": exc.code.value, "detail": messages[exc.code],
        "reason_codes": [item.value for item in exc.reasons],
        "current_revision": exc.current_revision,
    })


@app.exception_handler(InstitutionalIntelligenceServiceError)
async def handle_institutional_intelligence_service_error(
    _: Request, exc: InstitutionalIntelligenceServiceError
) -> JSONResponse:
    return JSONResponse(
        status_code=INSTITUTIONAL_INTELLIGENCE_HTTP_STATUS[exc.code],
        content={"kind": "error", "error_code": exc.code.value, "detail": exc.detail},
    )


@app.exception_handler(HTTPException)
async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code == 401:
        return JSONResponse(status_code=401, content={
            "kind": "error", "error_code": ServiceErrorCode.AUTH_REQUIRED.value,
            "detail": "Authentication is required", "reason_codes": [],
            "current_revision": None,
        })
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail},
                        headers=exc.headers)


@app.exception_handler(StudyPlanNotFound)
async def handle_study_plan_not_found(_: Request, __: StudyPlanNotFound) -> JSONResponse:
    return _catalog_error_response("STUDY_PLAN_NOT_FOUND", "Study plan was not found", 404)


@app.exception_handler(TargetCourseNotFound)
async def handle_target_not_found(_: Request, __: TargetCourseNotFound) -> JSONResponse:
    return _catalog_error_response("TARGET_NOT_FOUND", "Target course was not found", 404)


@app.exception_handler(TargetCourseNotInStudyPlan)
async def handle_target_not_in_plan(_: Request, __: TargetCourseNotInStudyPlan) -> JSONResponse:
    return _catalog_error_response(
        "TARGET_NOT_IN_STUDY_PLAN",
        "Target course is not in the requested study plan",
        409,
    )


@app.exception_handler(CatalogIntegrityError)
@app.exception_handler(ProgressIntegrityError)
@app.exception_handler(PlannerIntegrityError)
@app.exception_handler(DegreePathIntegrityError)
async def handle_catalog_integrity(_: Request, __: Exception) -> JSONResponse:
    return _catalog_error_response("CATALOG_INTEGRITY_ERROR", "Catalog integrity error", 500)


@app.exception_handler(DegreePathConstraintError)
async def handle_degree_path_constraint(_: Request, exc: DegreePathConstraintError) -> JSONResponse:
    return _catalog_error_response("DEGREE_PATH_CONSTRAINT_INVALID", str(exc), 422)


@app.exception_handler(CatalogTransportError)
async def handle_catalog_transport(_: Request, __: CatalogTransportError) -> JSONResponse:
    return _catalog_error_response("CATALOG_TRANSPORT_ERROR", "Catalog service unavailable", 503)


@app.exception_handler(EligibilityConfigurationError)
async def handle_catalog_configuration(_: Request, __: EligibilityConfigurationError) -> JSONResponse:
    return _catalog_error_response(
        "CATALOG_CONFIGURATION_ERROR",
        "Catalog service is not configured",
        503,
    )


@app.exception_handler(StudentProfileNotFound)
@app.exception_handler(StudentAttemptNotFound)
@app.exception_handler(StudentCourseNotFound)
@app.exception_handler(StudentStudyPlanNotFound)
async def handle_student_not_found(_: Request, __: Exception) -> JSONResponse:
    return _catalog_error_response("STUDENT_RESOURCE_NOT_FOUND", "Student resource was not found", 404)


@app.exception_handler(StudentProfileAlreadyExists)
async def handle_profile_conflict(_: Request, __: StudentProfileAlreadyExists) -> JSONResponse:
    return _catalog_error_response("STUDENT_PROFILE_ALREADY_EXISTS", "Student profile already exists", 409)


@app.exception_handler(StudentCourseUniversityMismatch)
async def handle_course_mismatch(_: Request, __: StudentCourseUniversityMismatch) -> JSONResponse:
    return _catalog_error_response("STUDENT_COURSE_UNIVERSITY_MISMATCH", "Course does not belong to the profile university", 409)


@app.exception_handler(StudentProfileIntegrityError)
async def handle_student_integrity(_: Request, __: StudentProfileIntegrityError) -> JSONResponse:
    return _catalog_error_response("STUDENT_INTEGRITY_ERROR", "Student data integrity error", 500)


@app.exception_handler(StudentProfileTransportError)
@app.exception_handler(StudentConfigurationError)
async def handle_student_unavailable(_: Request, __: Exception) -> JSONResponse:
    return _catalog_error_response("STUDENT_SERVICE_UNAVAILABLE", "Student service unavailable", 503)


@app.exception_handler(StudentProfileValidationError)
async def handle_student_validation(_: Request, __: StudentProfileValidationError) -> JSONResponse:
    return _catalog_error_response("STUDENT_PROFILE_INVALID", "Student profile facts are invalid", 422)


@app.exception_handler(AdvisorConfigurationError)
async def handle_advisor_configuration(_: Request, __: AdvisorConfigurationError) -> JSONResponse:
    return _catalog_error_response(
        "ADVISOR_SERVICE_UNAVAILABLE",
        "Advisor service is not configured",
        503,
    )


@app.exception_handler(AdvisorProviderError)
async def handle_advisor_provider(_: Request, exc: AdvisorProviderError) -> JSONResponse:
    failure_type = exc.failure.failure_type
    if failure_type is ProviderFailureType.TIMEOUT:
        return _catalog_error_response(
            "ADVISOR_PROVIDER_TIMEOUT",
            "Advisor interpretation provider timed out",
            503,
        )
    if failure_type is ProviderFailureType.PROVIDER_UNAVAILABLE:
        return _catalog_error_response(
            "ADVISOR_PROVIDER_UNAVAILABLE",
            "Advisor interpretation provider is unavailable",
            503,
        )
    return _catalog_error_response(
        "ADVISOR_PROVIDER_RESPONSE_INVALID",
        "Advisor interpretation provider returned an invalid response",
        502,
    )
