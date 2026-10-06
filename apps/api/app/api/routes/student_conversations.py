"""Authenticated, owner-derived student conversation history and continuation."""

from __future__ import annotations

import asyncio
import re
from typing import Annotated
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.api.routes.advisor import get_advisor_service
from app.api.routes.student import get_student_service
from app.api.schemas.advisor import AdvisorResponse
from app.core.auth import CurrentUser, get_current_user
from app.services.advisor import AdvisorService
from app.services.student import StudentService
from app.student_conversation.context import (
    bounded_conversation_context,
    extract_explicit_memories,
    extract_explicit_preferences,
)
from app.student_conversation.store import (ConversationNotFound, ConversationUnavailable,
                                            SupabaseConversationStore)


def _generate_arabic_title(first_message: str) -> str:
    cleaned = first_message.strip()
    if re.search(r"(?:معدلي|gpa|المعدل)", cleaned, re.I):
        return "المعدل التراكمي والسجل الأكاديمي"
    if re.search(r"(?:ساع[ةه]|ساعات|ضايل|باقي|تخرج)", cleaned, re.I):
        return "الساعات المتبقية ومتطلبات التخرج"
    if re.search(r"(?:شو\s+المواد|شو\s+انزل|شو\s+اسجل|بتنصحني|اقترح|متاحة)", cleaned, re.I):
        return "المساقات الموصى بها للتسجيل"
    course_code_match = re.search(r"(?<!\d)\d{6,8}(?!\d)", cleaned)
    if course_code_match:
        return f"استفسار عن مساق {course_code_match.group(0)}"
    if len(cleaned) <= 35:
        return cleaned
    return cleaned[:35].rstrip() + "..."

router = APIRouter(prefix="/api/v1/me/conversations", tags=["student-conversations"],
                   dependencies=[Depends(get_current_user)])
User = Annotated[CurrentUser, Depends(get_current_user)]
Student = Annotated[StudentService, Depends(get_student_service)]
Advisor = Annotated[AdvisorService, Depends(get_advisor_service)]


class NewThread(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(default="New conversation", min_length=1, max_length=120)


class NewMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=4000)
    client_message_id: UUID


class RenameThread(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=120)


class MessageReply(BaseModel):
    thread_id: UUID
    user_message: dict
    assistant_message: dict
    advisor: AdvisorResponse


def _store(request: Request) -> SupabaseConversationStore:
    store = getattr(request.app.state, "student_conversation_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="Conversation storage unavailable")
    return store


async def _scope(user: CurrentUser, student: StudentService) -> tuple[str, str, str]:
    owner = str(user.user_id)
    state, institution = await asyncio.gather(
        student.get_profile(owner), student.resolve_student_university_id(owner))
    return owner, institution, state.profile_id


def _not_found(error: ConversationNotFound) -> HTTPException:
    return HTTPException(status_code=404, detail="Conversation not found")


@router.get("")
async def list_threads(user: User, student: Student, request: Request,
                       offset: int = 0) -> list[dict]:
    if offset < 0 or offset > 100000:
        raise HTTPException(status_code=422, detail="Invalid history offset")
    owner, institution, _ = await _scope(user, student)
    return await _store(request).list_threads(owner, institution, offset=offset)


@router.post("", status_code=201)
async def create_thread(body: NewThread, user: User, student: Student, request: Request) -> dict:
    owner, institution, profile_id = await _scope(user, student)
    return await _store(request).create_thread(owner, institution, profile_id, body.title.strip())


@router.get("/preferences")
async def get_preferences(user: User, student: Student, request: Request) -> dict[str, str]:
    owner, institution, _ = await _scope(user, student)
    return await _store(request).active_preferences(owner, institution)


@router.get("/memories")
async def get_memories(user: User, student: Student, request: Request) -> list[dict]:
    owner, institution, _ = await _scope(user, student)
    store = _store(request)
    if hasattr(store, "active_memories"):
        return await store.active_memories(owner, institution)
    return []


@router.get("/{thread_id}/messages")
async def get_messages(thread_id: UUID, user: User, student: Student, request: Request,
                       offset: int = 0) -> list[dict]:
    if offset < 0 or offset > 100000:
        raise HTTPException(status_code=422, detail="Invalid history offset")
    owner, institution, _ = await _scope(user, student)
    try:
        return await _store(request).list_messages(owner, institution, str(thread_id), offset=offset)
    except ConversationNotFound as error:
        raise _not_found(error) from error


@router.patch("/{thread_id}")
async def rename_thread(thread_id: UUID, body: RenameThread, user: User,
                        student: Student, request: Request) -> dict:
    owner, institution, _ = await _scope(user, student)
    try:
        return await _store(request).update_thread(
            owner, institution, str(thread_id), {"title": body.title.strip()})
    except ConversationNotFound as error:
        raise _not_found(error) from error


@router.post("/{thread_id}/archive")
async def archive_thread(thread_id: UUID, user: User, student: Student, request: Request) -> dict:
    owner, institution, _ = await _scope(user, student)
    try:
        return await _store(request).update_thread(
            owner, institution, str(thread_id), {"status": "ARCHIVED"})
    except ConversationNotFound as error:
        raise _not_found(error) from error


@router.post("/{thread_id}/messages", response_model=MessageReply)
async def continue_thread(thread_id: UUID, body: NewMessage, user: User, student: Student,
                          advisor: Advisor, request: Request) -> MessageReply:
    owner, institution, _ = await _scope(user, student)
    store = _store(request)
    try:
        thread = await store.get_thread(owner, institution, str(thread_id))
        if thread["status"] != "ACTIVE":
            raise ConversationNotFound("Conversation archived")
        if hasattr(store, "recent_thread_messages"):
            history_task = store.recent_thread_messages(owner, institution, str(thread_id), limit=20)
        else:
            history_task = store.recent_user_history(owner, institution)
        memories_task = store.active_memories(owner, institution) if hasattr(store, "active_memories") else asyncio.sleep(0, result=[])
        preferences, history, raw_memories = await asyncio.gather(
            store.active_preferences(owner, institution),
            history_task,
            memories_task,
        )
        memories: list[dict] = list(raw_memories) if isinstance(raw_memories, list) else []
        message = body.message.strip()
        if not message:
            raise HTTPException(status_code=422, detail="Message must not be blank")
        persisted_user_id = str(uuid5(
            NAMESPACE_URL,
            f"morshidi-user:{owner}:{institution}:{thread_id}:{body.client_message_id}",
        ))
        try:
            user_row = await store.get_message(
                owner, institution, str(thread_id), persisted_user_id)
            if user_row.get("role") != "USER" or user_row.get("content") != message:
                raise HTTPException(status_code=409, detail="Message retry identity conflict")
            user_created = False
        except ConversationNotFound:
            user_row = await store.append_message(
                owner, institution, str(thread_id), "USER", message, "USER_STATED",
                message_id=persisted_user_id)
            user_created = True
        if user_created and thread.get("title") in ("New conversation", "محادثة جديدة", "", None):
            new_title = _generate_arabic_title(message)
            try:
                await store.update_thread(owner, institution, str(thread_id), {"title": new_title})
            except Exception:
                pass
        changed = extract_explicit_preferences(message)
        if user_created:
            for key, value in changed.items():
                await store.save_preference(owner, institution, key, value, user_row["id"])
        preferences.update(changed)
        if changed:
            summary = "; ".join(f"{key}={preferences[key]}" for key in sorted(preferences))[:800]
            await store.update_thread(owner, institution, str(thread_id), {"summary_text": summary})

        changed_memories = extract_explicit_memories(message)
        if user_created and hasattr(store, "upsert_memory"):
            for mem in changed_memories:
                await store.upsert_memory(
                    owner, institution,
                    category=mem["category"],
                    key=mem["key"],
                    value=mem["value"],
                    source_thread_id=str(thread_id),
                )
        existing_mem_keys = {m.get("memory_key") for m in memories if isinstance(m, dict)}
        for mem in changed_memories:
            mem_dict = {
                "memory_category": mem["category"],
                "memory_key": mem["key"],
                "memory_value": mem["value"],
            }
            if mem["key"] in existing_mem_keys:
                for idx, m in enumerate(memories):
                    if m.get("memory_key") == mem["key"]:
                        memories[idx] = mem_dict
                        break
            else:
                memories.append(mem_dict)
                existing_mem_keys.add(mem["key"])

        result = await advisor.advise_with_explanation(
            owner, message, bounded_conversation_context(
                preferences, history, thread.get("summary_text"), memories=memories))
        response = AdvisorResponse.from_domain(
            result.structured_result, explanation=result.explanation,
            explanation_status=result.explanation_status,
            explanation_language=result.explanation_language,
        )
        display = response.explanation or "تمت معالجة استفسارك وفق القواعد الحتمية."
        assistant_id = str(uuid5(
            NAMESPACE_URL,
            f"morshidi-assistant:{owner}:{institution}:{thread_id}:{body.client_message_id}",
        ))
        try:
            assistant_row = await store.get_message(
                owner, institution, str(thread_id), assistant_id)
            if assistant_row.get("role") != "ASSISTANT":
                raise HTTPException(status_code=409, detail="Assistant retry identity conflict")
        except ConversationNotFound:
            assistant_row = await store.append_message(
                owner, institution, str(thread_id), "ASSISTANT", display,
                "GUARDED_PROVIDER" if response.explanation_status.value == "GENERATED"
                else "DETERMINISTIC_EXPLANATION", message_id=assistant_id)
        return MessageReply(thread_id=thread_id, user_message=user_row,
                            assistant_message=assistant_row, advisor=response)
    except ConversationNotFound as error:
        raise _not_found(error) from error
