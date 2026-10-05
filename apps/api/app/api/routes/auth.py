"""Authentication routes for Morshidi platform, including external university login."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from app.api.schemas.auth import (
    SessionData,
    SyncData,
    UniversityLoginErrorResponse,
    UniversityLoginRequest,
    UniversityLoginResponse,
    UserData,
)
from app.core.rate_limiter import (
    InMemoryLoginRateLimiter,
    default_login_rate_limiter,
    extract_client_ip,
)
from app.university_sync.admin_auth import MorshidiSession, SupabaseAdminAuthClient
from app.university_sync.errors import (
    InternalIdentityProvisionFailedError,
    InvalidUniversityCredentialsError,
    UniversityCourseNotMappedError,
    UniversityIdentityConflictError,
    UniversityPlanNotMappedError,
    UniversityProtocolError,
    UniversityRateLimitedError,
    UniversitySyncFailedError,
    UniversityUnavailableError,
)
from app.university_sync.service import UniversitySyncResult, UniversitySyncService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

NO_STORE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, private",
    "Pragma": "no-cache",
}


def get_university_sync_service(request: Request) -> UniversitySyncService:
    service = getattr(request.app.state, "university_sync_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"success": False, "error": "UNIVERSITY_UNAVAILABLE"},
        )
    return service


def get_supabase_admin_auth(request: Request) -> SupabaseAdminAuthClient:
    admin_auth = getattr(request.app.state, "admin_auth_client", None)
    if admin_auth is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"success": False, "error": "UNIVERSITY_UNAVAILABLE"},
        )
    return admin_auth


def get_login_rate_limiter(request: Request) -> InMemoryLoginRateLimiter:
    limiter = getattr(request.app.state, "login_rate_limiter", None)
    if limiter is None:
        limiter = default_login_rate_limiter
    return limiter


def _error_response(status_code: int, error_code: str, headers: dict[str, str] | None = None) -> JSONResponse:
    merged_headers = dict(NO_STORE_HEADERS)
    if headers:
        merged_headers.update(headers)
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "error": error_code},
        headers=merged_headers,
    )


@router.post(
    "/university-login",
    response_model=UniversityLoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": UniversityLoginErrorResponse, "description": "Invalid university credentials"},
        409: {"model": UniversityLoginErrorResponse, "description": "Identity or email conflict"},
        422: {"model": UniversityLoginErrorResponse, "description": "Validation error"},
        429: {"model": UniversityLoginErrorResponse, "description": "Rate limited"},
        500: {"model": UniversityLoginErrorResponse, "description": "Internal session issuance failed"},
        503: {"model": UniversityLoginErrorResponse, "description": "University or academic sync unavailable"},
    },
)
async def university_login(
    request: Request,
    response: Response,
    body: UniversityLoginRequest,
    sync_service: Annotated[UniversitySyncService, Depends(get_university_sync_service)],
    admin_auth: Annotated[SupabaseAdminAuthClient, Depends(get_supabase_admin_auth)],
    rate_limiter: Annotated[InMemoryLoginRateLimiter, Depends(get_login_rate_limiter)],
) -> UniversityLoginResponse:
    """Authenticate via external university student credentials and issue an internal Morshidi Supabase session.

    Security Invariants:
    - University credentials exist only transiently in memory and are never logged or stored.
    - Upstream Fake University integration tokens are never exposed or returned to the browser.
    - Returned access/refresh tokens represent the internal Morshidi Supabase Auth identity.
    - Responses have explicit Cache-Control: no-store protection.
    """
    # 1. Apply rate limit check
    client_ip = extract_client_ip(request)
    is_allowed, retry_after = rate_limiter.check_rate_limit(client_ip)
    if not is_allowed:
        return _error_response(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMITED",
            headers={"Retry-After": str(retry_after)},
        )

    clean_student_id = body.student_id.strip()
    raw_password = body.password.get_secret_value()

    # 2. Authenticate and Synchronize via UniversitySyncService
    try:
        sync_result: UniversitySyncResult = await sync_service.authenticate_and_sync_student(
            clean_student_id, raw_password
        )
    except InvalidUniversityCredentialsError:
        # Uniform 401 error: does not reveal student account existence or password correctness
        logger.info("University login failed: invalid credentials for student ID %s", clean_student_id[:3] + "***")
        return _error_response(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS")
    except UniversityRateLimitedError as err:
        headers = {"Retry-After": str(err.retry_after)} if err.retry_after else None
        return _error_response(status.HTTP_429_TOO_MANY_REQUESTS, "RATE_LIMITED", headers=headers)
    except (UniversityPlanNotMappedError, UniversityCourseNotMappedError) as err:
        logger.error("Academic sync failed mapping check: %s", err)
        return _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, "ACADEMIC_SYNC_UNAVAILABLE")
    except UniversityIdentityConflictError as err:
        logger.warning("University identity conflict: %s", err)
        return _error_response(status.HTTP_409_CONFLICT, "IDENTITY_CONFLICT")
    except (UniversityUnavailableError, UniversityProtocolError, UniversitySyncFailedError) as err:
        logger.error("University service unavailable or protocol error: %s", err)
        return _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, "UNIVERSITY_UNAVAILABLE")

    # 3. Issue Morshidi Supabase Auth user session
    shadow_password = sync_result._internal_shadow_password
    if not shadow_password:
        logger.error("UniversitySyncResult missing internal shadow password")
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "SESSION_ISSUANCE_FAILED")

    try:
        session: MorshidiSession = await admin_auth.issue_shadow_session(
            user_id=sync_result.owner_user_id,
            email=sync_result.canonical_email,
            shadow_password=shadow_password,
        )
    except InternalIdentityProvisionFailedError as err:
        logger.error("Session issuance failed for user %s: %s", sync_result.owner_user_id, err)
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "SESSION_ISSUANCE_FAILED")

    # 4. Attach no-store cache control headers to response
    for k, v in NO_STORE_HEADERS.items():
        response.headers[k] = v

    # 5. Return sanitized public response model
    return UniversityLoginResponse(
        success=True,
        session=SessionData(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            token_type=session.token_type,
            expires_in=session.expires_in,
            expires_at=session.expires_at,
        ),
        user=UserData(
            id=sync_result.owner_user_id,
            student_id=sync_result.university_student_id,
            email=sync_result.canonical_email,
        ),
        sync=SyncData(
            synced_at=sync_result.synced_at.isoformat(),
            courses_synced=sync_result.grades_count,
            attempts_synced=sync_result.grades_count,
            enrollments_synced=sync_result.enrollments_count,
        ),
    )
