"""Role-scoped, aggregate-only Institutional Intelligence V2 API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response

from app.core.auth import CurrentUser, get_current_user
from app.institutional_analytics.models import DashboardResponse, SimulationRequest, SimulationResponse
from app.institutional_analytics.service import InstitutionalAnalyticsError, InstitutionalAnalyticsService
from app.institutional_analytics.copilot import CopilotRequest, CopilotResponse, InstitutionalCopilotService

router = APIRouter(
    prefix="/api/v1/institutional/analytics", tags=["institutional-analytics"],
    dependencies=[Depends(get_current_user)],
)
User = Annotated[CurrentUser, Depends(get_current_user)]


def _service(request: Request) -> InstitutionalAnalyticsService:
    service = getattr(request.app.state, "institutional_analytics_service", None)
    if service is None:
        raise InstitutionalAnalyticsError(
            "INSTITUTIONAL_ANALYTICS_UNAVAILABLE", 503, "Institutional analytics are unavailable")
    return service


Service = Annotated[InstitutionalAnalyticsService, Depends(_service)]


def _copilot(request: Request) -> InstitutionalCopilotService:
    service = getattr(request.app.state, "institutional_copilot_service", None)
    if service is None:
        raise InstitutionalAnalyticsError(
            "INSTITUTIONAL_COPILOT_UNAVAILABLE", 503, "Institutional Copilot is unavailable")
    return service


Copilot = Annotated[InstitutionalCopilotService, Depends(_copilot)]


@router.get("/access")
async def access(user: User, service: Service, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return {"kind": "INSTITUTIONAL_ACCESS", "scopes": await service.access(user.user_id)}


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard(
    user: User, service: Service, response: Response,
    university_id: Annotated[UUID, Query()], term_key: Annotated[str, Query(min_length=1, max_length=80)] = "CURRENT",
    faculty: Annotated[str | None, Query(max_length=50)] = None,
    major: Annotated[str | None, Query(max_length=50)] = None,
    plan_key: Annotated[str | None, Query(max_length=100)] = None,
) -> DashboardResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.dashboard(
        user.user_id, university_id=str(university_id), term_key=term_key,
        faculty=faculty, major=major, plan_key=plan_key,
    )


@router.get("/programs")
async def programs(
    user: User, service: Service, response: Response,
    university_id: Annotated[UUID, Query()], term_key: Annotated[str, Query(min_length=1, max_length=80)] = "CURRENT",
):
    response.headers["Cache-Control"] = "private, no-store"
    result = await service.dashboard(user.user_id, university_id=str(university_id), term_key=term_key)
    return {"kind": "PROGRAM_INTELLIGENCE", "items": result.programs, "generated_at": result.generated_at}


@router.get("/courses")
async def courses(
    user: User, service: Service, response: Response,
    university_id: Annotated[UUID, Query()], term_key: Annotated[str, Query(min_length=1, max_length=80)] = "CURRENT",
    course_code: Annotated[str | None, Query(max_length=50)] = None,
):
    response.headers["Cache-Control"] = "private, no-store"
    result = await service.dashboard(user.user_id, university_id=str(university_id), term_key=term_key)
    items = [item for item in result.courses if not course_code or item.course_code == course_code]
    return {"kind": "COURSE_INTELLIGENCE", "items": items, "generated_at": result.generated_at}


@router.get("/review-queue")
async def review_queue(
    user: User, service: Service, response: Response,
    university_id: Annotated[UUID, Query()], term_key: Annotated[str, Query(min_length=1, max_length=80)] = "CURRENT",
):
    response.headers["Cache-Control"] = "private, no-store"
    result = await service.dashboard(user.user_id, university_id=str(university_id), term_key=term_key)
    return {"kind": "REVIEW_REQUIRED_QUEUE", "items": result.review_queue,
            "system_behavior": "FAIL_CLOSED", "generated_at": result.generated_at}


@router.post("/simulate", response_model=SimulationResponse)
async def simulate(user: User, service: Service, body: SimulationRequest, response: Response) -> SimulationResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.simulate(user.user_id, body)


@router.post("/copilot", response_model=CopilotResponse)
async def copilot(user: User, service: Copilot, body: CopilotRequest, response: Response) -> CopilotResponse:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.ask(user.user_id, body)
