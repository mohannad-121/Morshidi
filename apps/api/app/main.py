from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.eligibility import router as eligibility_router
from app.api.routes.health import router as health_router
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


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Own one reusable server-side Data API client for the application lifetime."""

    client = httpx.AsyncClient()
    application.state.catalog_http_client = client
    application.state.eligibility_service = None
    if settings.supabase_url and settings.supabase_secret_key:
        repository = SupabaseAcademicCatalogRepository(
            settings.supabase_url,
            settings.supabase_secret_key.get_secret_value(),
            client,
        )
        application.state.eligibility_service = EligibilityService(repository)
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


def _catalog_error_response(error_code: str, detail: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"kind": "error", "error_code": error_code, "detail": detail},
    )


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
async def handle_catalog_integrity(_: Request, __: CatalogIntegrityError) -> JSONResponse:
    return _catalog_error_response("CATALOG_INTEGRITY_ERROR", "Catalog integrity error", 500)


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
