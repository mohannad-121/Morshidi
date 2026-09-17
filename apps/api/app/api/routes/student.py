"""Authenticated self-service profile, attempt, and eligibility routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.routes.eligibility import _decision_response
from app.api.schemas.eligibility import CanTakeDecisionResponse
from app.api.schemas.student import (
    AcademicProfileResponse, AttemptCreateRequest, AttemptUpdateRequest,
    CourseAttemptResponse, ProfileCreateRequest, ProfileUpdateRequest,
)
from app.api.schemas.progress import AcademicProgressResponse
from app.core.auth import CurrentUser, get_current_user
from app.rules.models import CanTakeDecision
from app.services.student import StudentConfigurationError, StudentService
from app.student.models import StudentAcademicState, StudentCourseAttemptRecord
from app.progress.models import AcademicProgress

router = APIRouter(prefix="/api/v1/me", tags=["student"], dependencies=[Depends(get_current_user)])
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


def get_student_service(request: Request) -> StudentService:
    service = getattr(request.app.state, "student_service", None)
    if service is None:
        raise StudentConfigurationError("Student service is not configured")
    return service


StudentServiceDependency = Annotated[StudentService, Depends(get_student_service)]


@router.get("/academic-profile", response_model=AcademicProfileResponse)
async def get_profile(user: AuthenticatedUser, service: StudentServiceDependency) -> AcademicProfileResponse:
    return _profile_response(await service.get_profile(user.user_id))


@router.get("/academic-progress", response_model=AcademicProgressResponse)
async def get_academic_progress(
    user: AuthenticatedUser,
    service: StudentServiceDependency,
) -> AcademicProgressResponse:
    return _progress_response(await service.get_academic_progress(user.user_id))


@router.post("/academic-profile", response_model=AcademicProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(body: ProfileCreateRequest, user: AuthenticatedUser, service: StudentServiceDependency) -> AcademicProfileResponse:
    return _profile_response(await service.create_profile(user.user_id, **body.model_dump()))


@router.patch("/academic-profile", response_model=AcademicProfileResponse)
async def update_profile(body: ProfileUpdateRequest, user: AuthenticatedUser, service: StudentServiceDependency) -> AcademicProfileResponse:
    return _profile_response(await service.update_profile(user.user_id, body.model_dump(exclude_unset=True)))


@router.delete("/academic-profile", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(user: AuthenticatedUser, service: StudentServiceDependency) -> Response:
    await service.delete_profile(user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/academic-profile/attempts", response_model=list[CourseAttemptResponse])
async def list_attempts(user: AuthenticatedUser, service: StudentServiceDependency) -> list[CourseAttemptResponse]:
    return [_attempt_response(row) for row in await service.list_attempts(user.user_id)]


@router.post("/academic-profile/attempts", response_model=CourseAttemptResponse, status_code=status.HTTP_201_CREATED)
async def create_attempt(body: AttemptCreateRequest, user: AuthenticatedUser, service: StudentServiceDependency) -> CourseAttemptResponse:
    values = body.model_dump()
    code, attempt_status = values.pop("course_code"), values.pop("status")
    values["reported_grade_text"] = values.pop("raw_grade_text")
    return _attempt_response(await service.create_attempt(user.user_id, code, attempt_status, **values))


@router.patch("/academic-profile/attempts/{attempt_id}", response_model=CourseAttemptResponse)
async def update_attempt(attempt_id: UUID, body: AttemptUpdateRequest, user: AuthenticatedUser, service: StudentServiceDependency) -> CourseAttemptResponse:
    return _attempt_response(await service.update_attempt(user.user_id, attempt_id, body.model_dump(exclude_unset=True)))


@router.delete("/academic-profile/attempts/{attempt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attempt(attempt_id: UUID, user: AuthenticatedUser, service: StudentServiceDependency) -> Response:
    await service.delete_attempt(user.user_id, attempt_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/eligibility/{target_course_code}", response_model=CanTakeDecisionResponse)
async def profile_can_take(target_course_code: str, user: AuthenticatedUser, service: StudentServiceDependency) -> CanTakeDecisionResponse:
    result = await service.evaluate_can_take(user.user_id, target_course_code)
    if not isinstance(result, CanTakeDecision):
        raise RuntimeError("Validated profile eligibility produced a request error")
    return _decision_response(result)


def _profile_response(state: StudentAcademicState) -> AcademicProfileResponse:
    return AcademicProfileResponse(id=state.profile_id, study_plan_id=state.study_plan_id,
        reported_cumulative_gpa=state.reported_cumulative_gpa,
        reported_gpa_scale=state.reported_gpa_scale,
        reported_earned_credit_hours=state.reported_earned_credit_hours,
        created_at=state.created_at, updated_at=state.updated_at)


def _attempt_response(row: StudentCourseAttemptRecord) -> CourseAttemptResponse:
    return CourseAttemptResponse(id=row.attempt_id, course_code=row.course_code, status=row.outcome,
        attempt_sequence=row.attempt_sequence, term_label=row.term_label, attempted_on=row.attempted_on,
        raw_grade_text=row.reported_grade_text, record_source=row.record_source,
        created_at=row.created_at, updated_at=row.updated_at)


def _progress_response(progress: AcademicProgress) -> AcademicProgressResponse:
    return AcademicProgressResponse.model_validate(progress, from_attributes=True)
