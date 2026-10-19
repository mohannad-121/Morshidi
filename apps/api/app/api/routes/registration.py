"""Authenticated student course-registration routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.auth import CurrentUser, get_current_user
from app.registration.service import RegistrationService, RegistrationUnavailableError
from app.university_sync.errors import (
    InvalidUniversityCredentialsError,
    UniversityProtocolError,
    UniversityRateLimitedError,
    UniversityUnavailableError,
)

router = APIRouter(prefix="/api/v1/me/registration", tags=["registration"],
                   dependencies=[Depends(get_current_user)])
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


class SectionSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_ids: list[str] = Field(min_length=1, max_length=12)

    @field_validator("section_ids")
    @classmethod
    def validate_ids(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value]
        if any(not item or len(item) > 100 for item in cleaned):
            raise ValueError("Invalid section identifier")
        return cleaned


class DropSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: str = Field(min_length=1, max_length=100)


def service(request: Request) -> RegistrationService:
    result = getattr(request.app.state, "registration_service", None)
    if result is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "UNIVERSITY_REGISTRATION_UNAVAILABLE")
    return result


def normalize_error(error: Exception) -> HTTPException:
    if isinstance(error, RegistrationUnavailableError):
        return HTTPException(status.HTTP_409_CONFLICT, str(error))
    if isinstance(error, InvalidUniversityCredentialsError):
        return HTTPException(status.HTTP_502_BAD_GATEWAY, "UNIVERSITY_SESSION_EXPIRED")
    if isinstance(error, UniversityRateLimitedError):
        return HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "UNIVERSITY_RATE_LIMITED")
    if isinstance(error, (UniversityProtocolError, UniversityUnavailableError)):
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "UNIVERSITY_REGISTRATION_UNAVAILABLE")
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "REGISTRATION_FAILED")


async def invoke(operation) -> dict[str, Any]:
    try:
        result = await operation
    except Exception as error:
        raise normalize_error(error) from error
    result.pop("_status_code", None)
    return result


@router.get("/context")
async def context(user: AuthenticatedUser, request: Request, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return await invoke(service(request).context(user.user_id))


@router.get("/offerings")
async def offerings(user: AuthenticatedUser, request: Request, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return await invoke(service(request).offerings(user.user_id))


@router.post("/preview")
async def preview(body: SectionSelection, user: AuthenticatedUser, request: Request, response: Response):
    response.headers["Cache-Control"] = "private, no-store"
    return await invoke(service(request).preview(user.user_id, body.section_ids))


def require_idempotency(value: str | None) -> str:
    key = (value or "").strip()
    if len(key) < 8 or len(key) > 200:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "IDEMPOTENCY_KEY_REQUIRED")
    return key


@router.post("/register")
async def register(body: SectionSelection, user: AuthenticatedUser, request: Request,
                   idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None):
    return await invoke(service(request).register(
        user.user_id, body.section_ids, require_idempotency(idempotency_key)
    ))


@router.post("/drop")
async def drop(body: DropSelection, user: AuthenticatedUser, request: Request,
               idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None):
    return await invoke(service(request).drop(
        user.user_id, body.section_id.strip(), require_idempotency(idempotency_key)
    ))
