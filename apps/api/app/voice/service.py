"""Domain service for Morshidi Realtime Live Voice sessions, WebRTC tokens, and academic delegation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from fastapi import HTTPException, status
import httpx

from app.advisor.tool_registry import advisor_tool_definitions
from app.services.advisor import AdvisorService
from app.services.student import StudentService
from app.student_conversation.context import (
    bounded_conversation_context,
    extract_explicit_memories,
    extract_explicit_preferences,
)
from app.voice.instructions import build_voice_system_instructions
from app.voice.session_manager import (
    VoiceQuotaExceededError,
    VoiceRateLimitError,
    VoiceSessionManager,
    VoiceSessionState,
)


logger = logging.getLogger(__name__)

OPENAI_LIVE_SESSIONS_URL = "https://api.openai.com/v1/live/sessions"
OPENAI_REALTIME_SESSIONS_URL = "https://api.openai.com/v1/realtime/sessions"
DEFAULT_VOICE_TIMEOUT_SECONDS = 20.0


class VoiceService:
    """Manages OpenAI Realtime / GPT-Live Voice session creation, WebRTC credentials, and academic tool delegation."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        advisor_service: AdvisorService,
        student_service: StudentService,
        session_manager: VoiceSessionManager,
        conversation_store: Any = None,
        policy_answer_service: Any = None,
        api_key: str | None = None,
        model: str = "gpt-live-1",
        voice_name: str = "alloy",
        max_duration_seconds: int = 900,
        enabled: bool = False,
    ) -> None:
        self._client = http_client
        self._advisor_service = advisor_service
        self._student_service = student_service
        self._session_manager = session_manager
        self._conversation_store = conversation_store
        self._policy_answer_service = policy_answer_service
        self._api_key = api_key.strip() if api_key and api_key.strip() else None
        self._model = model.strip() if model and model.strip() else "gpt-live-1"
        self._voice_name = voice_name.strip() if voice_name and voice_name.strip() else "alloy"
        self._max_duration_seconds = max_duration_seconds
        self._enabled = enabled

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def is_configured(self) -> bool:
        return self._api_key is not None

    def get_status(self, student_user_id: str) -> dict[str, Any]:
        """Check voice feature availability, remaining quota, and model information."""
        self._session_manager.cleanup_expired()
        quota = self._session_manager.get_quota_details(student_user_id)
        return {
            "enabled": self._enabled,
            "configured": self.is_configured,
            "model": self._model,
            "voice": self._voice_name,
            "max_duration_seconds": self._max_duration_seconds,
            "remaining_daily_quota": quota["remaining_daily_sessions"],
            "daily_usage": quota["used_daily_sessions"],
            "quota_details": quota,
        }

    async def create_realtime_session(
        self,
        student_user_id: str,
        thread_id: str | None = None,
        sdp_offer: str | None = None,
    ) -> dict[str, Any]:
        """Establish a live voice session with OpenAI.

        For gpt-live-1: Executes the official server-mediated SDP offer/answer exchange,
        connecting the browser directly via WebRTC without exposing any master API key.
        For gpt-realtime-2.1: Executes the Realtime API session handshake.
        """
        if not self._enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="المحادثة الصوتية المباشرة معطلة حالياً.",
            )

        if not self._api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="خدمة المحادثة الصوتية غير مهيأة (مفتاح API غير متوفر).",
            )

        try:
            self._session_manager.validate_can_start(student_user_id)
        except VoiceRateLimitError as err:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(err),
            ) from err
        except VoiceQuotaExceededError as err:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(err),
            ) from err

        # Resolve student institutional context strictly from server authentication
        try:
            university_id_task = self._student_service.resolve_student_university_id(student_user_id)
            profile_task = self._student_service.get_profile(student_user_id)
            university_id, profile = await asyncio.gather(university_id_task, profile_task)
        except Exception as exc:
            logger.warning("Failed to resolve student context for voice session: %s", exc)
            university_id = "UNKNOWN"
            profile = None

        # Build bounded conversation context if a thread is active
        bounded_context: str | None = None
        if thread_id and self._conversation_store is not None:
            try:
                store = self._conversation_store
                thread = await store.get_thread(student_user_id, str(university_id), str(thread_id))
                preferences_task = store.active_preferences(student_user_id, str(university_id))
                history_task = (
                    store.recent_thread_messages(student_user_id, str(university_id), str(thread_id), limit=10)
                    if hasattr(store, "recent_thread_messages")
                    else store.recent_user_history(student_user_id, str(university_id))
                )
                memories_task = (
                    store.active_memories(student_user_id, str(university_id))
                    if hasattr(store, "active_memories")
                    else asyncio.sleep(0, result=[])
                )
                preferences, history, memories = await asyncio.gather(
                    preferences_task, history_task, memories_task
                )
                bounded_context = bounded_conversation_context(
                    preferences, history, thread.get("summary_text"), memories=memories
                )
            except Exception as exc:
                logger.info("Proceeding with fresh conversation context for voice: %s", exc)
                bounded_context = None

        instructions = build_voice_system_instructions(
            university_name_ar=getattr(profile, "university_name_ar", None) or f"جامعة {university_id}",
            university_name_en=getattr(profile, "university_name_en", None),
            grading_scale="مقياس الجامعة المعتمد",
            bounded_context=bounded_context,
            active_dialect="msa",
        )

        tools = list(advisor_tool_definitions(include_what_if=True, include_voice_extensions=True))
        is_live = "live" in self._model.lower()

        if is_live:
            # Official GPT-Live server-mediated WebRTC SDP exchange
            target_url = OPENAI_LIVE_SESSIONS_URL
            payload = {
                "session": {
                    "model": self._model,
                    "voice": self._voice_name,
                    "instructions": instructions,
                    "delegation": {"type": "client"},
                    "modalities": ["audio", "text"],
                    "turn_detection": {
                        "type": "server_vad",
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 500,
                        "create_response": True,
                    },
                },
                "transport": {
                    "type": "webrtc",
                    "sdp": sdp_offer or "",
                },
            }
        else:
            # Explicit gpt-realtime-2.1 fallback flow
            target_url = OPENAI_REALTIME_SESSIONS_URL
            payload = {
                "model": self._model,
                "voice": self._voice_name,
                "modalities": ["audio", "text"],
                "instructions": instructions,
                "input_audio_transcription": {
                    "model": "whisper-1",
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                    "create_response": True,
                },
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.6,
                "max_response_output_tokens": 1024,
            }

        try:
            response = await self._client.post(
                target_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=DEFAULT_VOICE_TIMEOUT_SECONDS,
            )
        except httpx.TimeoutException as exc:
            logger.error("OpenAI session request timed out: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="استغرقت استجابة خادم الصوت وقتاً أطول من المتوقع. يرجى المحاولة لاحقاً.",
            ) from exc
        except httpx.RequestError as exc:
            logger.error("OpenAI session connection error: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="تعذر الاتصال بمزود خدمة الصوت المباشر حالياً.",
            ) from exc

        if response.status_code in (401, 403):
            logger.error("OpenAI API authentication failed for voice session: %s", response.text)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="تعذر إنشاء جلسة صوتية: التحقق من مفتاح المزود غير صالح.",
            )
        if response.status_code == 429:
            logger.error("OpenAI API rate limit or quota exceeded: %s", response.text)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="تم تجاوز حد الاستخدام لدى مزود خدمة الصوت المباشر. يرجى المحاولة لاحقاً.",
            )
        if response.status_code >= 400:
            logger.error("OpenAI voice session creation error %d: %s", response.status_code, response.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="تعذر تجهيز الجلسة الصوتية مع مزود الذكاء الاصطناعي.",
            )

        try:
            data = response.json()
            session_id = data.get("id") or data.get("session", {}).get("id") or "sess_live"
            sdp_answer = None
            client_secret = None

            if is_live:
                sdp_answer = data.get("transport", {}).get("sdp") or data.get("sdp")
            else:
                client_secret_data = data.get("client_secret")
                if isinstance(client_secret_data, dict):
                    client_secret = client_secret_data.get("value")
                elif isinstance(client_secret_data, str):
                    client_secret = client_secret_data
                else:
                    client_secret = data.get("token") or data.get("client_token")
        except (KeyError, TypeError, ValueError) as exc:
            logger.error("Malformed OpenAI voice session response: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="استجابة مزود خدمة الصوت غير مكتملة.",
            ) from exc

        # Register active session in state manager
        session_state = self._session_manager.register_session(
            session_id=session_id,
            student_user_id=student_user_id,
            university_id=str(university_id),
            thread_id=thread_id,
            duration_seconds=self._max_duration_seconds,
        )

        logger.info(
            "voice_session_established student=%s session=%s model=%s university=%s",
            student_user_id, session_id, self._model, university_id,
        )

        return {
            "session_id": session_id,
            "sdp_answer": sdp_answer,
            "client_secret": client_secret,
            "model": self._model,
            "voice": self._voice_name,
            "endpoint_type": "live" if is_live else "realtime",
            "max_duration_seconds": session_state.max_duration_seconds,
            "default_language": session_state.language,
            "default_dialect": session_state.arabic_dialect,
            "tools": [t["name"] for t in tools],
            "university_id": str(university_id),
        }

    @staticmethod
    def _resolve_tool_from_context(tool_name: str | None, user_transcript: str | None) -> tuple[str, str]:
        """Resolve deterministic academic tool and arguments from delegation metadata or user transcript."""
        if tool_name and tool_name.strip():
            return tool_name.strip(), "{}"

        text = (user_transcript or "").strip()

        # Dialect Switch Triggers
        if any(w in text for w in ("أردني", "بالأردني", "عامية", "الأردن")):
            return "switch_dialect", json.dumps({"dialect": "jordanian"})
        if any(w in text for w in ("فصحى", "الفصحى", "العربية الفصحى")):
            return "switch_dialect", json.dumps({"dialect": "msa"})
        if any(w in text for w in ("english", "إنجليزي", "انجليزي")):
            return "switch_dialect", json.dumps({"dialect": "english"})

        # Academic Requirements Triggers
        if any(w in text for w in ("ساعات", "تخرج", "متطلبات", "فاضلي", "ضايل", "كم باقي")):
            return "get_remaining_requirements", "{}"

        # University Policy & Regulations Triggers
        if any(w in text for w in ("لائحة", "شرط", "إنذار", "شرف", "سياسة", "نظام", "مفصول")):
            return "search_university_policies", json.dumps({"query": text})

        # Course Eligibility / Offerings Triggers
        if any(w in text for w in ("مادة", "مواد", "مساق", "أهلية", "تسجيل", "أنزل")):
            return "get_eligible_courses", "{}"

        # Default to Academic Summary
        return "get_student_academic_summary", "{}"

    @staticmethod
    def _build_concise_commentary(tool_name: str, output: Any, user_transcript: str | None = None) -> str:
        """Construct concise, verified Arabic commentary (< 800 chars) for GPT-Live session.commentary.append."""
        if not isinstance(output, dict):
            return str(output)[:800]

        if not output.get("ok", True):
            return "تعذر استرجاع المعلومة الأكاديمية المطلوبة حالياً من السجلات المعتمدة."

        if tool_name == "get_remaining_requirements":
            hours = output.get("remaining_credit_hours")
            reqs = output.get("requirements_left")
            req_str = f" والمواد المتبقية تشمل: {', '.join(str(r) for r in reqs[:3])}" if reqs else ""
            return f"بحسب خطتك الدراسية المعتمدة، يتبقى عليك {hours} ساعة معتمدة لإتمام التخرج{req_str}."

        if tool_name == "get_student_academic_summary":
            gpa = output.get("gpa", "")
            completed = output.get("completed_hours", "")
            standing = output.get("academic_standing", "جيد")
            return f"سجلك الأكاديمي المعتمد: المعدل التراكمي {gpa}، الساعات المنجزة {completed} ساعة، والوضع الأكاديمي {standing}."

        if tool_name == "get_course_eligibility":
            course = output.get("course_code", "")
            eligible = output.get("eligible", False)
            reason = output.get("reason", "")
            if eligible:
                return f"المادة {course} مؤهلة للتسجيل وتم استيفاء كافة المتطلبات السابقة."
            return f"المادة {course} غير متاحة للتسجيل حالياً: {reason}."

        if tool_name == "search_university_policies":
            ans = output.get("answer")
            if ans:
                return str(ans)[:800]
            return "لم يتم العثور على نص صريح لهذه المسألة في اللائحة الجامعية الحالية."

        if tool_name == "switch_dialect":
            dialect = output.get("dialect", "الأردنية")
            return f"تم اعتماد اللهجة المطلوبة للمحادثة الصوتية بنجاح."

        return json.dumps(output, ensure_ascii=False)[:800]

    async def execute_delegated_tool(
        self,
        *,
        student_user_id: str,
        call_id: str,
        tool_name: str | None = None,
        arguments: str = "{}",
        thread_id: str | None = None,
        user_transcript: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an authorized academic tool on the Morshidi backend on behalf of the voice session.

        Deterministic academic engines decide — the model only explains the verified output.
        """
        # Enforce server-authoritative session validity: expired sessions cannot execute academic delegation
        active_session = self._session_manager.get_active_session(student_user_id)
        if active_session is None:
            logger.warning("voice_delegation_rejected_expired student=%s call_id=%s", student_user_id, call_id)
            return {
                "call_id": call_id,
                "tool_name": tool_name or "unknown",
                "output": {"ok": False, "error": "SESSION_EXPIRED", "detail": "انتهت صلاحية الجلسة الصوتية المعتمدة."},
                "summary_text": "انتهت مدة الجلسة الصوتية المعتمدة. يرجى بدء محادثة صوتية جديدة أو متابعة استفسارك نصياً.",
                "ok": False,
            }

        try:
            university_id = await self._student_service.resolve_student_university_id(student_user_id)
        except Exception:
            university_id = None

        resolved_tool, resolved_args = self._resolve_tool_from_context(tool_name, user_transcript)
        actual_args = arguments if (tool_name and arguments and arguments != "{}") else resolved_args

        executor = self._advisor_service.build_tool_executor(
            student_user_id,
            university_id=str(university_id) if university_id else None,
            policy_answer_service=self._policy_answer_service,
        )

        try:
            executed = await executor.execute(resolved_tool, actual_args)
            output = getattr(executed, "output", executed)
        except Exception as exc:
            logger.error("Delegated tool execution error for %s: %s", resolved_tool, exc)
            output = {"ok": False, "error": "EXECUTION_ERROR", "details": str(exc)}

        # Synchronize dialect preference state if the tool requested a switch
        if resolved_tool == "switch_dialect" and isinstance(output, dict) and output.get("ok"):
            dialect = output.get("dialect", "msa")
            self._session_manager.update_dialect(student_user_id, dialect, "explicit_user_request")
            if thread_id and self._conversation_store is not None and university_id is not None:
                try:
                    await self._conversation_store.save_preference(
                        student_user_id, str(university_id), "spoken_dialect", dialect, "voice_session"
                    )
                except Exception as exc:
                    logger.debug("Non-critical dialect preference save failed: %s", exc)

        summary_text = self._build_concise_commentary(resolved_tool, output, user_transcript)

        # Refresh server-side session activity timestamp
        self._session_manager.touch_activity(student_user_id)

        logger.info(
            "voice_delegation_executed student=%s tool=%s call_id=%s ok=%s",
            student_user_id, resolved_tool, call_id,
            output.get("ok", True) if isinstance(output, dict) else True,
        )

        return {
            "call_id": call_id,
            "tool_name": resolved_tool,
            "output": output,
            "summary_text": summary_text,
            "ok": output.get("ok", True) if isinstance(output, dict) else True,
        }

    async def sync_completed_turn(
        self,
        *,
        student_user_id: str,
        thread_id: str,
        user_transcript: str,
        assistant_transcript: str,
        client_turn_id: UUID,
    ) -> dict[str, Any]:
        """Persist a completed voice conversation turn into the active student thread.

        Prevents duplicate entries via deterministic UUID generation and keeps text and
        voice histories aligned without saving partial or interim speech fragments.
        """
        user_text = user_transcript.strip()
        assistant_text = assistant_transcript.strip()
        if not user_text or not assistant_text:
            return {"synced": False, "reason": "empty_turn"}

        if self._conversation_store is None:
            return {"synced": False, "reason": "storage_unavailable"}

        try:
            university_id = await self._student_service.resolve_student_university_id(student_user_id)
        except Exception:
            university_id = "UNKNOWN"

        store = self._conversation_store
        persisted_user_id = str(uuid5(
            NAMESPACE_URL,
            f"morshidi-voice-user:{student_user_id}:{university_id}:{thread_id}:{client_turn_id}",
        ))
        persisted_assistant_id = str(uuid5(
            NAMESPACE_URL,
            f"morshidi-voice-assistant:{student_user_id}:{university_id}:{thread_id}:{client_turn_id}",
        ))

        try:
            user_row = await store.append_message(
                student_user_id, str(university_id), str(thread_id),
                "USER", user_text, "USER_SPOKEN",
                message_id=persisted_user_id,
            )
            assistant_row = await store.append_message(
                student_user_id, str(university_id), str(thread_id),
                "ASSISTANT", assistant_text, "VOICE_ADVISOR",
                message_id=persisted_assistant_id,
            )

            # Extract any stated planning preferences from the spoken turn
            changed = extract_explicit_preferences(user_text)
            for k, v in changed.items():
                await store.save_preference(student_user_id, str(university_id), k, v, user_row["id"])

            changed_memories = extract_explicit_memories(user_text)
            if hasattr(store, "upsert_memory"):
                for mem in changed_memories:
                    await store.upsert_memory(
                        student_user_id, str(university_id),
                        category=mem["category"],
                        key=mem["key"],
                        value=mem["value"],
                        source_thread_id=str(thread_id),
                    )

            # Update session activity timestamp (prevents abandonment timeout)
            self._session_manager.touch_activity(student_user_id)

            logger.info("voice_turn_synced student=%s thread=%s turn=%s", student_user_id, thread_id, client_turn_id)
            return {
                "synced": True,
                "user_message_id": user_row.get("id"),
                "assistant_message_id": assistant_row.get("id"),
            }
        except Exception as exc:
            logger.warning("Voice turn synchronization failed non-critically: %s", exc)
            return {"synced": False, "error": str(exc)}

    def end_session(
        self,
        student_user_id: str,
        session_id: str | None = None,
        actual_duration_seconds: float | None = None,
    ) -> float:
        """Mark the active voice session as terminated, clean up state, and reconcile actual duration."""
        duration = self._session_manager.end_session(
            student_user_id,
            session_id,
            actual_duration_seconds=actual_duration_seconds,
        )
        logger.info("voice_session_ended student=%s session=%s duration=%.1fs", student_user_id, session_id, duration)
        return duration

