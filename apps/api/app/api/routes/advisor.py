"""Authenticated, read-only advisor HTTP boundary."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.schemas.advisor import AdvisorRequest, AdvisorResponse
from app.core.auth import CurrentUser, get_current_user
from app.services.advisor import AdvisorConfigurationError, AdvisorService


router = APIRouter(
    prefix="/api/v1/me",
    tags=["advisor"],
    dependencies=[Depends(get_current_user)],
)
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


def get_advisor_service(request: Request) -> AdvisorService:
    service = getattr(request.app.state, "advisor_service", None)
    if service is None:
        raise AdvisorConfigurationError("Advisor service is not configured")
    return service


AdvisorServiceDependency = Annotated[AdvisorService, Depends(get_advisor_service)]


@router.post("/advisor", response_model=AdvisorResponse)
async def advise(
    body: AdvisorRequest,
    user: AuthenticatedUser,
    service: AdvisorServiceDependency,
) -> AdvisorResponse:
    result = await service.advise_with_explanation(user.user_id, body.message)
    return AdvisorResponse.from_domain(
        result.structured_result,
        explanation=result.explanation,
        explanation_status=result.explanation_status,
        explanation_language=result.explanation_language,
    )
