"""Authenticated student-facing Realtime Live Voice endpoints with client delegation."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.auth import CurrentUser, get_current_user
from app.voice.service import VoiceService


router = APIRouter(
    prefix="/api/v1/me/voice",
    tags=["voice"],
    dependencies=[Depends(get_current_user)],
)

User = Annotated[CurrentUser, Depends(get_current_user)]


def get_voice_service(request: Request) -> VoiceService:
    service = getattr(request.app.state, "voice_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="خدمة المحادثة الصوتية غير متاحة حالياً.",
        )
    return service


VoiceServiceDep = Annotated[VoiceService, Depends(get_voice_service)]


class VoiceSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: UUID | None = None
    sdp_offer: str | None = None


class VoiceSessionResponse(BaseModel):
    session_id: str
    sdp_answer: str | None = None
    client_secret: str | None = None
    expires_at: int | None = None
    model: str
    voice: str
    endpoint_type: str = "live"
    max_duration_seconds: int
    default_language: str
    default_dialect: str
    tools: list[str]
    university_id: str


class VoiceDelegateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    call_id: str = Field(min_length=1, max_length=120)
    tool_name: str | None = Field(default=None, max_length=120)
    arguments: str = Field(default="{}", max_length=4000)
    thread_id: UUID | None = None
    user_transcript: str | None = Field(default=None, max_length=4000)
    metadata: dict[str, Any] | None = None


class VoiceDelegateResponse(BaseModel):
    call_id: str
    tool_name: str
    output: Any
    summary_text: str | None = None
    ok: bool = True


class VoiceTurnSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    thread_id: UUID
    user_transcript: str = Field(min_length=1, max_length=4000)
    assistant_transcript: str = Field(min_length=1, max_length=4000)
    client_turn_id: UUID


class VoiceTurnSyncResponse(BaseModel):
    synced: bool
    user_message_id: str | None = None
    assistant_message_id: str | None = None
    error: str | None = None


class VoiceStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    model: str
    voice: str
    max_duration_seconds: int
    remaining_daily_quota: int
    daily_usage: int


class VoiceEndSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str | None = None
    actual_duration_seconds: float | None = None


@router.get("/status", response_model=VoiceStatusResponse)
async def get_status(
    user: User,
    voice_service: VoiceServiceDep,
) -> VoiceStatusResponse:
    """Check live voice availability, quota limits, and configured voice model."""
    status_data = voice_service.get_status(str(user.user_id))
    return VoiceStatusResponse.model_validate(status_data)


@router.post("/session", response_model=VoiceSessionResponse)
async def create_session(
    body: VoiceSessionRequest,
    user: User,
    voice_service: VoiceServiceDep,
) -> VoiceSessionResponse:
    """Establish a secure WebRTC live voice session with OpenAI.

    For GPT-Live, performs server-mediated SDP offer/answer exchange.
    The master project API key is strictly maintained server-side.
    """
    session_data = await voice_service.create_realtime_session(
        student_user_id=str(user.user_id),
        thread_id=str(body.thread_id) if body.thread_id else None,
        sdp_offer=body.sdp_offer,
    )
    return VoiceSessionResponse.model_validate(session_data)


@router.post("/delegate", response_model=VoiceDelegateResponse)
async def delegate_tool(
    body: VoiceDelegateRequest,
    user: User,
    voice_service: VoiceServiceDep,
) -> VoiceDelegateResponse:
    """Execute authorized academic intelligence tools on the Morshidi backend.

    Client delegation keeps deterministic rules as the sole authority.
    The LLM voice model explains verified results returned by this endpoint.
    """
    result = await voice_service.execute_delegated_tool(
        student_user_id=str(user.user_id),
        call_id=body.call_id,
        tool_name=body.tool_name,
        arguments=body.arguments,
        thread_id=str(body.thread_id) if body.thread_id else None,
        user_transcript=body.user_transcript,
        metadata=body.metadata,
    )
    return VoiceDelegateResponse.model_validate(result)


@router.post("/sync-turn", response_model=VoiceTurnSyncResponse)
async def sync_turn(
    body: VoiceTurnSyncRequest,
    user: User,
    voice_service: VoiceServiceDep,
) -> VoiceTurnSyncResponse:
    """Persist completed speech turn transcripts into the student's conversation history."""
    result = await voice_service.sync_completed_turn(
        student_user_id=str(user.user_id),
        thread_id=str(body.thread_id),
        user_transcript=body.user_transcript,
        assistant_transcript=body.assistant_transcript,
        client_turn_id=body.client_turn_id,
    )
    return VoiceTurnSyncResponse.model_validate(result)


@router.post("/end-session")
async def end_session(
    body: VoiceEndSessionRequest,
    user: User,
    voice_service: VoiceServiceDep,
) -> dict[str, bool]:
    """Gracefully terminate an active voice session and reconcile consumed quota minutes."""
    voice_service.end_session(
        student_user_id=str(user.user_id),
        session_id=body.session_id,
        actual_duration_seconds=body.actual_duration_seconds,
    )
    return {"ok": True}

