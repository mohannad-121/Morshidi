"""Closed, read-only tool contracts for the student conversational advisor."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoArguments(_StrictArguments):
    pass


class CourseReferenceArguments(_StrictArguments):
    course_reference: str = Field(min_length=1, max_length=120)


class CompareCoursesArguments(_StrictArguments):
    first_course_reference: str = Field(min_length=1, max_length=120)
    second_course_reference: str = Field(min_length=1, max_length=120)


class SemesterPlanArguments(_StrictArguments):
    max_credit_hours: Decimal | None = Field(default=None, ge=0, le=30)
    max_courses: int | None = Field(default=None, ge=1, le=10)


class DegreePathArguments(_StrictArguments):
    max_credit_hours_per_semester: Decimal | None = Field(default=None, ge=0, le=30)
    max_courses_per_semester: int | None = Field(default=None, ge=1, le=10)
    max_semesters_ahead: int = Field(default=8, ge=1, le=16)
    max_paths: int = Field(default=3, ge=1, le=5)


class WhatIfArguments(_StrictArguments):
    operation: Literal["MODEL_COURSE_COMPLETION", "OMIT_NEXT_PLAN_COURSE", "SET_PLANNING_CONSTRAINTS"]
    course_reference: str | None = Field(default=None, min_length=1, max_length=120)
    max_credit_hours: Decimal | None = Field(default=None, ge=0, le=30)
    max_courses: int | None = Field(default=None, ge=1, le=10)


TOOL_ARGUMENT_MODELS: dict[str, type[_StrictArguments]] = {
    "get_student_academic_summary": NoArguments,
    "get_student_intelligence": NoArguments,
    "get_course_eligibility": CourseReferenceArguments,
    "get_eligible_courses": NoArguments,
    "get_course_recommendations": NoArguments,
    "get_course_information": CourseReferenceArguments,
    "compare_courses": CompareCoursesArguments,
    "get_remaining_requirements": NoArguments,
    "get_semester_plan": SemesterPlanArguments,
    "get_degree_path": DegreePathArguments,
    "run_academic_what_if": WhatIfArguments,
    "get_current_enrollments": NoArguments,
    "get_student_progress": NoArguments,
}


_DESCRIPTIONS = {
    "get_student_academic_summary": "Get bounded official academic facts for the authenticated student, including GPA when available, earned credits, attempts, and progress. Use before making claims about the student's record.",
    "get_student_intelligence": "Get bounded Student Intelligence V2 skills, confidence, evidence counts, strengths, development areas, reasoning patterns, and limitations. It never returns raw diagnostic answers or answer keys.",
    "get_course_eligibility": "Use the deterministic eligibility engine for one course. The result, not the model, decides eligibility and prerequisite blockers.",
    "get_eligible_courses": "Get the deterministic currently eligible course set. Never add courses outside this result.",
    "get_course_recommendations": "Get deterministic eligible course recommendations and bounded personalization. Personal fit never changes eligibility.",
    "get_course_information": "Get canonical catalog facts for one course, including prerequisites and modeled difficulty when available.",
    "compare_courses": "Compare exactly two canonical courses using catalog facts and deterministic modeled evidence.",
    "get_remaining_requirements": "Get deterministic completed and remaining degree requirement facts.",
    "get_semester_plan": "Get deterministic next-semester plan options under bounded constraints.",
    "get_degree_path": "Get deterministic modeled multi-semester degree path options under bounded constraints.",
    "run_academic_what_if": "Run an existing deterministic, ephemeral What-If operation. This never persists or changes the student's record.",
    "get_current_enrollments": "Get bounded current in-progress course codes from the authenticated student's official record.",
    "get_student_progress": "Get deterministic degree progress and requirement completion facts.",
}


def _strict_schema(model: type[_StrictArguments]) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema.pop("title", None)
    _remove_unsupported_provider_keywords(schema)
    schema["additionalProperties"] = False
    # OpenAI strict function schemas require every property to be named in
    # ``required``; nullable/defaulted fields are still emitted explicitly.
    schema["required"] = list(schema.get("properties", {}))
    return schema


def _remove_unsupported_provider_keywords(value: object) -> None:
    """Remove validation annotations outside OpenAI's strict schema subset.

    Pydantic emits a regex with negative lookahead for ``Decimal`` string
    coercion. OpenAI rejects regex lookaround in strict function schemas, while
    the executor still applies the full Pydantic validation after tool
    selection.
    """

    if isinstance(value, dict):
        value.pop("pattern", None)
        for nested in value.values():
            _remove_unsupported_provider_keywords(nested)
    elif isinstance(value, list):
        for nested in value:
            _remove_unsupported_provider_keywords(nested)


def advisor_tool_definitions(*, include_what_if: bool = False) -> tuple[dict[str, Any], ...]:
    """Return OpenAI function definitions without identity or tenant arguments."""

    names = tuple(TOOL_ARGUMENT_MODELS)
    if not include_what_if:
        names = tuple(name for name in names if name != "run_academic_what_if")
    return tuple(
        {
            "type": "function",
            "name": name,
            "description": _DESCRIPTIONS[name],
            "parameters": _strict_schema(TOOL_ARGUMENT_MODELS[name]),
            "strict": True,
        }
        for name in names
    )
