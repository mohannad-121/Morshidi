from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import re
from datetime import datetime
from time import monotonic
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.university_sync.events import UniversityEventStore

router = APIRouter(prefix="/api/v1", tags=["university live events"])
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]
EventType = Literal[
    "grade.posted", "record.updated", "registration.opened", "registration.closed",
    "offering.updated", "section.opened", "section.closed", "schedule.changed", "plan.updated",
]
SSE_HEARTBEAT_SECONDS = 15.0


class UniversityEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    type: EventType
    version: int = Field(ge=1)
    occurredAt: datetime
    studentId: str | None = Field(default=None, pattern=r"^\d{9}$")
    payload: dict[str, object]
    idempotencyKey: str = Field(min_length=1, max_length=160)

    @field_validator("occurredAt")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("event timestamp must include a timezone")
        return value

    @model_validator(mode="after")
    def require_private_event_scope(self):
        if self.type in {"grade.posted", "record.updated", "schedule.changed", "plan.updated"} and self.studentId is None:
            raise ValueError("student scope required for private event")
        return self


def _event_store(request: Request) -> UniversityEventStore:
    store = getattr(request.app.state, "university_event_store", None)
    if store is None:
        raise HTTPException(503, detail={"kind": "error", "code": "EVENT_STORE_UNAVAILABLE"})
    return store


def integration_university_id() -> str:
    try:
        return str(UUID(settings.uni_university_id or ""))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(503, detail={"kind": "error", "code": "UNIVERSITY_IDENTITY_UNAVAILABLE"}) from None


async def resolve_student_scope(request: Request, user: CurrentUser) -> tuple[str, str]:
    repository = getattr(request.app.state, "university_identity_repository", None)
    university_id = integration_university_id()
    if repository is None or not university_id:
        raise HTTPException(503, detail={"kind": "error", "code": "UNIVERSITY_IDENTITY_UNAVAILABLE"})
    try:
        identity = await repository.get_university_identity_for_user(user.user_id, university_id)
    except Exception:
        raise HTTPException(503, detail={"kind": "error", "code": "UNIVERSITY_IDENTITY_UNAVAILABLE"}) from None
    student_id = getattr(identity, "university_student_id", None)
    if (identity is None or str(getattr(identity, "owner_user_id", "")) != str(user.user_id)
            or str(getattr(identity, "university_id", "")) != university_id
            or not isinstance(student_id, str) or not re.fullmatch(r"[0-9]{9}", student_id)):
        raise HTTPException(403, detail={"kind": "error", "code": "STUDENT_SCOPE_REQUIRED"})
    return university_id, student_id


def verify_signature(raw: bytes, signature: str | None, secret: str | None) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest() if secret else ""
    return bool(secret and signature and re.fullmatch(r"sha256=[0-9a-f]{64}", signature)
                and hmac.compare_digest(expected, signature))


@router.post("/uni/webhook", status_code=202)
async def receive_university_event(request: Request, x_uni_signature: str | None = Header(default=None)):
    secret = settings.uni_webhook_secret.get_secret_value() if settings.uni_webhook_secret else ""
    if not secret.strip():
        raise HTTPException(503, detail={"kind": "error", "code": "WEBHOOK_NOT_CONFIGURED"})
    raw = await request.body()
    if len(raw) > 128 * 1024:
        raise HTTPException(413, detail={"kind": "error", "code": "EVENT_TOO_LARGE"})
    if not verify_signature(raw, x_uni_signature, secret):
        raise HTTPException(401, detail={"kind": "error", "code": "INVALID_EVENT_SIGNATURE"})
    university_id = integration_university_id()
    try:
        parsed = UniversityEvent.model_validate_json(raw)
    except ValueError:
        raise HTTPException(422, detail={"kind": "error", "code": "INVALID_EVENT"}) from None
    try:
        return await _event_store(request).ingest(university_id, parsed.model_dump(by_alias=True, mode="json"))
    except Exception:
        raise HTTPException(503, detail={"kind": "error", "code": "EVENT_STORE_UNAVAILABLE"}) from None


@router.get("/me/university-notifications")
async def my_university_notifications(user: AuthenticatedUser, request: Request, since: str | None = None):
    try:
        university_id, student_id = await resolve_student_scope(request, user)
        return await _event_store(request).list_notifications(university_id, student_id, since)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, detail={"kind": "error", "code": "NOTIFICATIONS_UNAVAILABLE"}) from None


@router.get("/me/university-stream")
async def my_university_stream(user: AuthenticatedUser, request: Request, since: str | None = None):
    university_id, student_id = await resolve_student_scope(request, user)
    store = _event_store(request)

    async def stream():
        cursor: int | None = None
        last_emit_at = monotonic()
        yield "retry: 3000\n\n"
        while not await request.is_disconnected():
            # Reuse the same Auth verification as the initial request. Check
            # the mapping before each poll so a revoked or moved identity
            # cannot receive another batch after revocation is observed.
            scheme, token = get_authorization_scheme_param(request.headers.get("authorization"))
            credentials = HTTPAuthorizationCredentials(scheme=scheme, credentials=token) if scheme and token else None
            try:
                current_user = await get_current_user(request, credentials)
                if current_user.user_id != user.user_id:
                    return
                if await resolve_student_scope(request, current_user) != (university_id, student_id):
                    return
            except HTTPException:
                return
            try:
                rows = await store.list_notifications(university_id, student_id, since if cursor is None else None, after_id=cursor)
                frames = []
                for row in sorted(rows, key=lambda row: row["id"]):
                    payload = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                    frames.append(f"data: {payload}\n\n")
                    if isinstance(row.get("id"), int):
                        cursor = row["id"]
                if frames:
                    yield "".join(frames)
                    last_emit_at = monotonic()
                elif monotonic() - last_emit_at >= SSE_HEARTBEAT_SECONDS:
                    # SSE comments keep idle proxy connections active without
                    # inventing an event, cursor, or client-visible message.
                    yield ": keep-alive\n\n"
                    last_emit_at = monotonic()
            except Exception:
                yield "event: sync-error\ndata: {}\n\n"
                last_emit_at = monotonic()
            await asyncio.sleep(3)

    return StreamingResponse(stream(), media_type="text/event-stream; charset=utf-8", headers={
        "Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no",
    })
