"""Owner-scoped P14 local contract; no production provider is installed by default."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import CurrentUser, get_current_user
from app.p14_privacy.domain import DataCategory, MeasureKind
from app.p14_privacy.store import LocalPrivacyStore, PrivacyDenied
from app.services.student import StudentService

router = APIRouter(prefix="/api/v1/me/privacy", tags=["privacy-p14"])
User = Annotated[CurrentUser, Depends(get_current_user)]


class ClosedBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConsentBody(ClosedBody):
    study_id: str = Field(min_length=1, max_length=80)


class PrivacyRequestBody(ClosedBody):
    kind: str
    category: DataCategory
    reason: str = Field(min_length=1, max_length=500)
    source_reference: str | None = Field(default=None, max_length=160)


class MeasureBody(ClosedBody):
    task_id: str = Field(min_length=1, max_length=80)
    kind: MeasureKind
    value: int = Field(ge=0, le=1800)
    accessibility_flags: tuple[str, ...] = ()


class FeedbackBody(ClosedBody):
    clarity: int = Field(ge=1, le=5)
    usefulness: int = Field(ge=1, le=5)
    understanding: int = Field(ge=1, le=5)
    workload: int = Field(ge=1, le=5)
    accessibility_issue: bool
    comment: str | None = Field(default=None, max_length=280)


async def _scope(user: CurrentUser, request: Request, response: Response) -> tuple[LocalPrivacyStore, str]:
    store: LocalPrivacyStore | None = getattr(request.app.state, "p14_privacy_store", None)
    student: StudentService | None = getattr(request.app.state, "student_service", None)
    if store is None or student is None:
        raise HTTPException(503, "PRIVACY_PROVIDER_UNAVAILABLE")
    institution = await student.resolve_student_university_id(user.user_id)
    response.headers["Cache-Control"] = "private, no-store"
    return store, institution


@router.get("")
async def privacy_summary(user: User, request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    return store.summary(user.user_id, institution)


@router.post("/consents")
async def grant_consent(body: ConsentBody, user: User, request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    try:
        return store.grant_study_consent(user.user_id, institution, body.study_id)
    except PrivacyDenied:
        raise HTTPException(404, "STUDY_UNAVAILABLE") from None


@router.post("/consents/{consent_id}/withdraw")
async def withdraw_consent(consent_id: str, user: User, request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    try:
        return store.withdraw(user.user_id, institution, consent_id)
    except PrivacyDenied:
        raise HTTPException(404, "CONSENT_UNAVAILABLE") from None


@router.post("/requests")
async def create_request(body: PrivacyRequestBody, user: User, request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    try:
        return store.request(user.user_id, institution, body.kind, body.category,
                             body.reason, body.source_reference)
    except PrivacyDenied:
        raise HTTPException(404, "OPTIONAL_DATA_UNAVAILABLE") from None
    except ValueError:
        raise HTTPException(422, "INVALID_PRIVACY_REQUEST") from None


@router.get("/requests/{request_id}")
async def get_request(request_id: str, user: User, request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    try:
        return store.get_request(user.user_id, institution, request_id)
    except PrivacyDenied:
        raise HTTPException(404, "REQUEST_UNAVAILABLE") from None


@router.post("/export")
async def export_privacy_data(user: User, request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    return store.export(user.user_id, institution)


@router.post("/studies/{study_id}/join")
async def join_study(study_id: str, user: User, request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    try:
        return store.study_join(user.user_id, institution, study_id)
    except PrivacyDenied:
        raise HTTPException(404, "STUDY_UNAVAILABLE") from None


@router.get("/studies")
async def available_studies(user: User, request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    return {"studies": store.available_studies(user.user_id, institution),
            "label": "SYNTHETIC STUDY — NO REAL PARTICIPANTS"}


@router.post("/studies/{study_id}/measures")
async def submit_measure(study_id: str, body: MeasureBody, user: User,
                         request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    try:
        return store.measure(user.user_id, institution, study_id, body.task_id,
                             body.kind, body.value, body.accessibility_flags)
    except PrivacyDenied:
        raise HTTPException(404, "STUDY_UNAVAILABLE") from None
    except ValueError:
        raise HTTPException(422, "INVALID_MEASURE") from None


@router.post("/studies/{study_id}/feedback")
async def submit_feedback(study_id: str, body: FeedbackBody, user: User,
                          request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    try:
        return store.feedback(user.user_id, institution, study_id, body.clarity,
                              body.usefulness, body.understanding, body.workload,
                              body.accessibility_issue, body.comment)
    except PrivacyDenied:
        raise HTTPException(404, "STUDY_UNAVAILABLE") from None
    except ValueError:
        raise HTTPException(422, "INVALID_FEEDBACK") from None


@router.get("/feedback/{feedback_id}")
async def get_feedback(feedback_id: str, user: User, request: Request, response: Response):
    store, institution = await _scope(user, request, response)
    try:
        return store.feedback_item(user.user_id, institution, feedback_id)
    except PrivacyDenied:
        raise HTTPException(404, "FEEDBACK_UNAVAILABLE") from None
