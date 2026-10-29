"""Owner-injected execution boundary for conversational advisor tools."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from decimal import Decimal
from enum import Enum
import json
from typing import Any, Awaitable, Callable

from pydantic import ValidationError

from app.advisor.conversation_agent import ExecutedTool
from app.advisor.provider import RawAdvisorInterpretation
from app.advisor.student_intelligence_context import (
    project_course_fit,
    project_student_intelligence,
)
from app.advisor.tool_registry import ALL_TOOL_ARGUMENT_MODELS, TOOL_ARGUMENT_MODELS
from app.student.models import StudentAcademicState
from app.student_intelligence.adaptive import AdaptiveCourseResult
from app.student_intelligence.curriculum_mapping import UnsupportedCurriculumIntelligenceError
from app.student_intelligence.profile_v2 import StudentIntelligenceProfileV2
from app.recommendations.models import RecommendationResult


LegacyRunner = Callable[
    [RawAdvisorInterpretation, str], Awaitable[object]
]
StateLoader = Callable[[str], Awaitable[StudentAcademicState]]
IntelligenceLoader = Callable[[str], Awaitable[StudentIntelligenceProfileV2]]
AdaptiveLoader = Callable[[str], Awaitable[AdaptiveCourseResult]]
WhatIfRunner = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class AdvisorToolExecutor:
    """Validate model arguments and execute only allowlisted read-only operations."""

    def __init__(
        self,
        *,
        owner_user_id: str,
        run_legacy: LegacyRunner,
        load_state: StateLoader,
        load_intelligence: IntelligenceLoader | None,
        load_adaptive: AdaptiveLoader | None = None,
        run_what_if: WhatIfRunner | None = None,
        policy_answer_service: Any = None,
        university_id: str | None = None,
    ) -> None:
        self._owner_user_id = owner_user_id
        self._run_legacy = run_legacy
        self._load_state = load_state
        self._load_intelligence = load_intelligence
        self._load_adaptive = load_adaptive
        self._run_what_if = run_what_if
        self._policy_answer_service = policy_answer_service
        self._university_id = university_id

    async def execute(self, name: str, raw_arguments: str) -> ExecutedTool:
        model = ALL_TOOL_ARGUMENT_MODELS.get(name) or TOOL_ARGUMENT_MODELS.get(name)
        if model is None:
            return ExecutedTool(name, _tool_error("UNKNOWN_TOOL"))
        try:
            decoded = json.loads(raw_arguments)
            if not isinstance(decoded, dict):
                raise ValueError
            arguments = model.model_validate(decoded)
        except (json.JSONDecodeError, TypeError, ValueError, ValidationError):
            return ExecutedTool(name, _tool_error("INVALID_ARGUMENTS"))

        if name == "get_student_intelligence":
            if self._load_intelligence is None:
                return ExecutedTool(name, _tool_error("EVIDENCE_UNAVAILABLE"))
            try:
                bounded = project_student_intelligence(
                    await self._load_intelligence(self._owner_user_id)
                )
                payload = asdict(bounded) if is_dataclass(bounded) else bounded
                return ExecutedTool(name, {"ok": True, "result": _json_safe(payload)})
            except UnsupportedCurriculumIntelligenceError:
                return ExecutedTool(
                    name,
                    {
                        "ok": False,
                        "error": "STUDENT_INTELLIGENCE_UNSUPPORTED_CURRICULUM",
                        "message": "Discipline-specific Student Intelligence is not available for this curriculum.",
                    },
                )

        if name == "get_current_enrollments":
            state = await self._load_state(self._owner_user_id)
            current = sorted(
                {
                    attempt.course_code
                    for attempt in state.attempts
                    if getattr(attempt.outcome, "value", str(attempt.outcome)) == "IN_PROGRESS"
                }
            )
            return ExecutedTool(
                name,
                {
                    "ok": True,
                    "result": {"current_course_codes": current, "count": len(current)},
                    "limitations": ["Only authoritative in-progress attempt records are included."],
                },
            )

        if name == "run_academic_what_if":
            if self._run_what_if is None:
                return ExecutedTool(name, _tool_error("TOOL_NOT_AVAILABLE"))
            output = await self._run_what_if(
                self._owner_user_id, arguments.model_dump(mode="json")
            )
            return ExecutedTool(name, {"ok": True, "result": output})

        if name == "search_university_policies":
            if self._policy_answer_service is None or self._university_id is None:
                return ExecutedTool(name, _tool_error("POLICY_SERVICE_UNAVAILABLE"))
            try:
                result = await self._policy_answer_service.answer(self._university_id, arguments.query)
                evidence_list = []
                if hasattr(result, "evidence_passages"):
                    for e in result.evidence_passages:
                        evidence_list.append(_json_safe(asdict(e) if is_dataclass(e) else e))
                return ExecutedTool(
                    name,
                    {
                        "ok": True,
                        "question": arguments.query,
                        "answer": getattr(result, "answer_text", str(result)),
                        "has_answer": getattr(result, "has_answer", True),
                        "evidence": evidence_list,
                    },
                )
            except Exception:
                return ExecutedTool(name, _tool_error("POLICY_RETRIEVAL_FAILED"))

        if name == "switch_dialect":
            return ExecutedTool(
                name,
                {
                    "ok": True,
                    "dialect": getattr(arguments, "dialect", "msa"),
                    "message": f"Spoken dialect switched to {getattr(arguments, 'dialect', 'msa')}",
                },
            )

        raw, synthetic_message = _legacy_request(name, arguments.model_dump())
        if raw is None:
            return ExecutedTool(name, _tool_error("TOOL_NOT_AVAILABLE"))
        result = await self._run_legacy(raw, synthetic_message)
        payload = {"ok": True, "result": _json_safe(result)}
        authoritative_payload = getattr(result, "authoritative_payload", None)
        if (
            name == "get_course_recommendations"
            and self._load_adaptive is not None
            and isinstance(authoritative_payload, RecommendationResult)
        ):
            adaptive = await self._load_adaptive(self._owner_user_id)
            payload["personal_fit"] = _json_safe(
                project_course_fit(adaptive, authoritative_payload)
            )
            payload["personal_fit_limitation"] = (
                "Personal fit only ranks the deterministic eligible set and never changes eligibility."
            )
        return ExecutedTool(
            name,
            payload,
            result,
        )


def _legacy_request(
    name: str, arguments: dict[str, Any]
) -> tuple[RawAdvisorInterpretation | None, str]:
    if name in {"get_student_academic_summary", "get_student_progress"}:
        return RawAdvisorInterpretation("ACADEMIC_STATUS"), "my academic progress"
    if name == "get_remaining_requirements":
        return RawAdvisorInterpretation("REMAINING_REQUIREMENTS"), "my remaining requirements"
    if name in {"get_eligible_courses", "get_course_recommendations"}:
        return RawAdvisorInterpretation("COURSE_RECOMMENDATIONS"), "recommended eligible courses"
    if name == "get_course_eligibility":
        reference = str(arguments["course_reference"])
        return (
            RawAdvisorInterpretation("COURSE_ELIGIBILITY", course_mentions=(reference,)),
            f"Can I take course {reference}?",
        )
    if name == "get_course_information":
        reference = str(arguments["course_reference"])
        return (
            RawAdvisorInterpretation("COURSE_INFORMATION", course_mentions=(reference,)),
            f"Information about course {reference}",
        )
    if name == "compare_courses":
        first = str(arguments["first_course_reference"])
        second = str(arguments["second_course_reference"])
        return (
            RawAdvisorInterpretation("COURSE_COMPARISON", course_mentions=(first, second)),
            f"Compare courses {first} and {second}",
        )
    if name == "get_semester_plan":
        return (
            RawAdvisorInterpretation(
                "SEMESTER_PLANNING",
                max_credit_hours_per_semester=arguments.get("max_credit_hours"),
                max_courses_per_semester=arguments.get("max_courses"),
            ),
            "Plan my next semester",
        )
    if name == "get_degree_path":
        return (
            RawAdvisorInterpretation(
                "DEGREE_PATH_MODELING",
                max_credit_hours_per_semester=arguments.get("max_credit_hours_per_semester"),
                max_courses_per_semester=arguments.get("max_courses_per_semester"),
                max_semesters_ahead=arguments.get("max_semesters_ahead"),
                max_paths=arguments.get("max_paths"),
            ),
            "Model my degree path",
        )
    return None, ""


def _tool_error(code: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error": code,
        "message": "The tool request was not executed. Use another safe tool or explain the limitation.",
    }


def _json_safe(value: Any) -> Any:
    """Serialize typed deterministic results without transport-layer imports."""

    if is_dataclass(value):
        return _json_safe(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
