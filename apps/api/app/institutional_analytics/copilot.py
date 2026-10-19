"""Bounded Institutional Copilot: a model may select a tool; deterministic services supply facts."""

from __future__ import annotations

import json
import re
from enum import Enum
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from .models import SimulationRequest
from .service import InstitutionalAnalyticsService


class InstitutionalTool(str, Enum):
    OVERVIEW = "get_institution_overview"
    PROGRAM = "get_program_metrics"
    COURSE_DEMAND = "get_course_demand"
    BOTTLENECKS = "get_bottlenecks"
    CAPACITY = "get_capacity_pressure"
    PROGRESS = "get_progress_distribution"
    REVIEW_QUEUE = "get_review_queue"
    SIMULATE_CAPACITY = "simulate_section_capacity"


class CopilotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=8, max_length=400)
    university_id: str
    term_key: str = Field(min_length=1, max_length=80)
    previous_tool: InstitutionalTool | None = None
    previous_course_code: str | None = Field(default=None, max_length=50)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        return " ".join(value.split())


class ToolSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    tool: InstitutionalTool | None = None
    course_code: str | None = None
    major_code: str | None = None
    seats: int | None = Field(default=None, ge=1, le=500)
    reason: str | None = None


class CopilotResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    tool: InstitutionalTool | None = None
    answer_text: str
    result: dict[str, Any] | list[Any] | None = None
    course_code: str | None = None
    limitations: list[str] = Field(default_factory=list)


class ToolInterpreter(Protocol):
    async def select(self, request: CopilotRequest) -> ToolSelection: ...


class InterpreterUnavailable(RuntimeError):
    pass


class UnconfiguredToolInterpreter:
    async def select(self, request: CopilotRequest) -> ToolSelection:
        raise InterpreterUnavailable("Institutional Copilot provider is unavailable")


_UNSAFE = re.compile(
    r"\b(?:select|drop|insert|update|delete|sql|table|schema|password|token)\b|"
    r"(?:أسماء\s+الطلاب|بيانات\s+الطلاب|أرقامهم\s+الجامعية|اعطني\s+الطلاب)", re.IGNORECASE)


class InstitutionalCopilotService:
    def __init__(self, analytics: InstitutionalAnalyticsService, interpreter: ToolInterpreter) -> None:
        self._analytics = analytics
        self._interpreter = interpreter

    async def ask(self, subject: str, request: CopilotRequest) -> CopilotResponse:
        if _UNSAFE.search(request.question):
            return CopilotResponse(status="ABSTAINED", answer_text="لا يمكن عرض بيانات طلاب شخصية أو تنفيذ استعلامات حرة.",
                                   limitations=["AGGREGATE_ONLY", "NO_STUDENT_PII"])
        try:
            selection = await self._interpreter.select(request)
        except InterpreterUnavailable:
            return CopilotResponse(status="ABSTAINED", answer_text="المساعد المؤسسي غير متاح حاليًا.",
                                   limitations=["PROVIDER_UNAVAILABLE"])
        if selection.status != "SELECTED" or selection.tool is None:
            return CopilotResponse(status="ABSTAINED", answer_text="لم أجد أداة مؤسسية معتمدة تجيب عن هذا السؤال.",
                                   limitations=[selection.reason or "NO_APPROVED_TOOL"])
        course_code = (selection.course_code or request.previous_course_code or "").upper() or None
        dashboard = await self._analytics.dashboard(
            subject, university_id=request.university_id, term_key=request.term_key)
        tool = selection.tool
        result: dict[str, Any] | list[Any] | None
        if tool is InstitutionalTool.OVERVIEW:
            result = dashboard.overview.model_dump(mode="json")
        elif tool is InstitutionalTool.PROGRAM:
            items = dashboard.programs
            if selection.major_code:
                items = [item for item in items if item.major_code == selection.major_code.upper()]
            result = [item.model_dump(mode="json") for item in items]
        elif tool is InstitutionalTool.COURSE_DEMAND:
            items = dashboard.courses
            if course_code:
                items = [item for item in items if item.course_code == course_code]
            else:
                items = sorted(items, key=lambda item: (-(item.projected_demand.value or 0), item.course_code))[:10]
            result = [item.model_dump(mode="json") for item in items]
        elif tool is InstitutionalTool.BOTTLENECKS:
            items = [item for item in dashboard.courses if item.bottleneck_level in {"HIGH", "CRITICAL"}]
            if course_code:
                items = [item for item in items if item.course_code == course_code]
            result = [item.model_dump(mode="json") for item in sorted(items, key=lambda item: -item.bottleneck_score)[:10]]
        elif tool is InstitutionalTool.CAPACITY:
            items = [item for item in dashboard.courses if item.capacity_state in {"NEAR_CAPACITY", "OVER_DEMAND"}]
            result = [item.model_dump(mode="json") for item in items]
        elif tool is InstitutionalTool.PROGRESS:
            result = [item.model_dump(mode="json") for item in dashboard.programs]
        elif tool is InstitutionalTool.REVIEW_QUEUE:
            result = [item.model_dump(mode="json") for item in dashboard.review_queue]
        else:
            if not course_code or selection.seats is None:
                return CopilotResponse(status="ABSTAINED", tool=tool,
                                       answer_text="المحاكاة تحتاج رمز مادة وعدد مقاعد واضحين.",
                                       limitations=["MISSING_SIMULATION_INPUT"])
            simulation = await self._analytics.simulate(subject, SimulationRequest(
                university_id=request.university_id, term_key=request.term_key,
                course_code=course_code, kind="ADD_SECTION", seats=selection.seats))
            result = simulation.model_dump(mode="json")
        return CopilotResponse(
            status="ANSWERED", tool=tool, result=result, course_code=course_code,
            answer_text=_deterministic_summary(tool, result),
            limitations=["DETERMINISTIC_TOOL_OUTPUT", "AGGREGATE_ONLY", "NO_MUTATION"],
        )


def _deterministic_summary(tool: InstitutionalTool, result: dict[str, Any] | list[Any] | None) -> str:
    if tool is InstitutionalTool.SIMULATE_CAPACITY and isinstance(result, dict):
        return (f"المحاكاة فقط: فجوة الطلب تنتقل من {result.get('demand_gap_before')} إلى "
                f"{result.get('demand_gap_after')}، والعدد المحسوب للطلبة المستفيدين {result.get('estimated_students_helped')}.")
    if tool is InstitutionalTool.OVERVIEW and isinstance(result, dict):
        total = result.get("total_active_students", {}).get("value")
        return f"النظرة المؤسسية الحالية مبنية على {total} طالبًا نشطًا ضمن النطاق المصرح."
    if isinstance(result, list):
        return f"أعادت الأداة المؤسسية المعتمدة {len(result)} نتيجة حتمية. التفاصيل أدناه كما حسبها النظام."
    return "أعادت الأداة المؤسسية نتيجة حتمية قابلة للتدقيق."


class OpenAIToolInterpreter:
    URL = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str, model: str, client: httpx.AsyncClient) -> None:
        self._api_key, self._model, self._client = api_key, model, client

    async def select(self, request: CopilotRequest) -> ToolSelection:
        schema = ToolSelection.model_json_schema()
        prompt = {
            "question": request.question,
            "available_tools": [item.value for item in InstitutionalTool],
            "previous_tool": request.previous_tool.value if request.previous_tool else None,
            "previous_course_code": request.previous_course_code,
            "rules": ["Select exactly one listed read-only tool or abstain.",
                      "Never calculate, estimate, or invent a metric.",
                      "Never request student identities or raw records.",
                      "For simulation extract a course code and explicit seat count."],
        }
        try:
            response = await self._client.post(self.URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self._model,
                      "instructions": "Select an approved deterministic institutional tool. Return only the schema.",
                      "input": json.dumps(prompt, ensure_ascii=False), "store": False,
                      "text": {"format": {"type": "json_schema", "name": "institutional_tool_selection",
                                            "strict": True, "schema": schema}}}, timeout=20)
            response.raise_for_status()
            body = response.json()
            texts = [part.get("text") for item in body.get("output", []) if item.get("type") == "message"
                     for part in item.get("content", []) if part.get("type") == "output_text"]
            if len(texts) != 1:
                raise ValueError("missing structured selection")
            return ToolSelection.model_validate_json(texts[0])
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as error:
            raise InterpreterUnavailable("Institutional Copilot provider is unavailable") from error
