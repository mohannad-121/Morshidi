"""Semantic orchestration tests for the bounded conversational advisor loop."""

from __future__ import annotations

import json

import pytest

from app.advisor.conversation_agent import (
    ConversationAgentResult,
    ConversationToolCall,
    ConversationTurn,
    ExecutedTool,
    run_conversation_agent,
)
from app.advisor.provider import ProviderFailure, ProviderFailureType
from app.advisor.tool_executor import AdvisorToolExecutor
from app.advisor.tool_registry import advisor_tool_definitions


class FakeConversationProvider:
    def __init__(self, turns: list[object]) -> None:
        self.turns = list(turns)
        self.inputs: list[list[dict]] = []
        self.tools: list[tuple[dict, ...]] = []

    async def converse(self, *, input_items, tools):  # type: ignore[no-untyped-def]
        self.inputs.append(list(input_items))
        self.tools.append(tools)
        return self.turns.pop(0)


def _call(call_id: str, name: str, arguments: str = "{}") -> ConversationTurn:
    item = {
        "type": "function_call",
        "call_id": call_id,
        "name": name,
        "arguments": arguments,
    }
    return ConversationTurn((item,), (ConversationToolCall(call_id, name, arguments),))


@pytest.mark.anyio
async def test_general_chat_is_one_provider_call_and_zero_tools() -> None:
    provider = FakeConversationProvider([ConversationTurn((), text="تمام، كيف أساعدك؟")])
    executed: list[str] = []

    async def execute(name: str, arguments: str) -> ExecutedTool:
        executed.append(name)
        return ExecutedTool(name, {"ok": True})

    result = await run_conversation_agent(
        provider, message="كيفك؟", conversation_context="", tools=advisor_tool_definitions(),
        execute_tool=execute,
    )
    assert isinstance(result, ConversationAgentResult)
    assert result.answer == "تمام، كيف أساعدك؟"
    assert result.tools_called == ()
    assert executed == []
    assert len(provider.inputs) == 1


@pytest.mark.anyio
async def test_exact_self_understanding_question_calls_student_intelligence() -> None:
    provider = FakeConversationProvider([
        _call("call_1", "get_student_intelligence"),
        ConversationTurn((), text="معرفتي الحالية مبنية على التشخيص الأولي."),
    ])

    async def execute(name: str, arguments: str) -> ExecutedTool:
        assert arguments == "{}"
        return ExecutedTool(name, {"ok": True, "result": {"official_evidence_count": 0, "diagnostic_evidence_count": 30}})

    result = await run_conversation_agent(
        provider, message="شو بتعرف عني؟", conversation_context="", tools=advisor_tool_definitions(),
        execute_tool=execute,
    )
    assert isinstance(result, ConversationAgentResult)
    assert result.tools_called == ("get_student_intelligence",)
    assert len(provider.inputs) == 2
    second_input = provider.inputs[1]
    assert second_input[0]["role"] == "user"
    assert second_input[-1]["type"] == "function_call_output"
    assert second_input[-1]["call_id"] == "call_1"


@pytest.mark.anyio
async def test_multi_intent_executes_multiple_tool_calls_before_final_answer() -> None:
    first = ConversationTurn(
        (
            {"type": "function_call", "call_id": "a", "name": "get_eligible_courses", "arguments": "{}"},
            {"type": "function_call", "call_id": "b", "name": "get_student_intelligence", "arguments": "{}"},
            {"type": "function_call", "call_id": "c", "name": "get_course_recommendations", "arguments": "{}"},
        ),
        (
            ConversationToolCall("a", "get_eligible_courses", "{}"),
            ConversationToolCall("b", "get_student_intelligence", "{}"),
            ConversationToolCall("c", "get_course_recommendations", "{}"),
        ),
    )
    provider = FakeConversationProvider([first, ConversationTurn((), text="هاي الخيارات الأنسب ضمن المواد المؤهلة.")])
    order: list[str] = []

    async def execute(name: str, arguments: str) -> ExecutedTool:
        order.append(name)
        return ExecutedTool(name, {"ok": True, "result": {"source": name}})

    result = await run_conversation_agent(
        provider,
        message="شو المواد اللي بقدر أنزلها وأي وحدة أنسب إلي وليش؟",
        conversation_context="",
        tools=advisor_tool_definitions(),
        execute_tool=execute,
    )
    assert isinstance(result, ConversationAgentResult)
    assert order == ["get_eligible_courses", "get_student_intelligence", "get_course_recommendations"]
    assert result.tools_called == tuple(order)
    outputs = provider.inputs[1][-3:]
    assert [item["call_id"] for item in outputs] == ["a", "b", "c"]


@pytest.mark.anyio
async def test_follow_up_context_is_bounded_input_for_reference_resolution() -> None:
    provider = FakeConversationProvider([
        _call("call_ml", "get_course_eligibility", '{"course_reference":"Machine Learning"}'),
        ConversationTurn((), text="الأهلية تعتمد على المتطلبات الظاهرة."),
    ])

    async def execute(name: str, arguments: str) -> ExecutedTool:
        assert json.loads(arguments)["course_reference"] == "Machine Learning"
        return ExecutedTool(name, {"ok": True})

    result = await run_conversation_agent(
        provider,
        message="طيب أنا مؤهل إلها؟",
        conversation_context="USER: شو رأيك بمادة Machine Learning؟\nASSISTANT: مادة متقدمة.",
        tools=advisor_tool_definitions(),
        execute_tool=execute,
    )
    assert isinstance(result, ConversationAgentResult)
    prompt = provider.inputs[0][0]["content"][0]["text"]
    assert "Machine Learning" in prompt
    assert "never as academic fact" in prompt


@pytest.mark.anyio
async def test_tool_failure_is_returned_to_model_and_loop_can_recover() -> None:
    provider = FakeConversationProvider([
        _call("bad", "get_course_eligibility", "not-json"),
        ConversationTurn((), text="ما قدرت أتحقق من المادة؛ اكتب اسمها أو رمزها."),
    ])

    async def execute(name: str, arguments: str) -> ExecutedTool:
        raise ValueError("invalid")

    result = await run_conversation_agent(
        provider, message="هل بقدر أنزلها؟", conversation_context="", tools=advisor_tool_definitions(),
        execute_tool=execute,
    )
    assert isinstance(result, ConversationAgentResult)
    output = json.loads(provider.inputs[1][-1]["output"])
    assert output["error"] == "TOOL_EXECUTION_FAILED"
    assert result.limitations == ("get_course_eligibility:unavailable",)


@pytest.mark.anyio
async def test_internal_codes_are_never_returned_verbatim_to_student() -> None:
    provider = FakeConversationProvider([
        ConversationTurn((), text="الدليل MODELED_DIAGNOSTIC والحالة COLD_START_NO_PERFORMANCE_EVIDENCE.")
    ])

    async def execute(name: str, arguments: str) -> ExecutedTool:
        raise AssertionError("no tool expected")

    result = await run_conversation_agent(
        provider, message="شو الدليل؟", conversation_context="", tools=advisor_tool_definitions(),
        execute_tool=execute,
    )
    assert isinstance(result, ConversationAgentResult)
    assert "MODELED_DIAGNOSTIC" not in result.answer
    assert "COLD_START_NO_PERFORMANCE_EVIDENCE" not in result.answer
    assert "مبني على التشخيص الأولي" in result.answer


@pytest.mark.anyio
async def test_provider_failure_and_round_limit_are_safe() -> None:
    failure = ProviderFailure(ProviderFailureType.TIMEOUT, "advisor.provider.timeout")
    provider = FakeConversationProvider([failure])

    async def execute(name: str, arguments: str) -> ExecutedTool:
        return ExecutedTool(name, {"ok": True})

    result = await run_conversation_agent(
        provider, message="hello", conversation_context="", tools=advisor_tool_definitions(),
        execute_tool=execute,
    )
    assert result is failure

    looping = FakeConversationProvider([_call(str(index), "get_student_progress") for index in range(5)])
    limited = await run_conversation_agent(
        looping, message="وضعي؟", conversation_context="", tools=advisor_tool_definitions(),
        execute_tool=execute,
    )
    assert isinstance(limited, ProviderFailure)
    assert limited.message_key == "advisor.conversation.tool_round_limit"


def test_tool_schemas_are_strict_read_only_and_never_accept_identity() -> None:
    definitions = advisor_tool_definitions()
    assert len(definitions) == 12
    for definition in definitions:
        encoded = json.dumps(definition)
        assert definition["type"] == "function"
        assert definition["strict"] is True
        assert definition["parameters"]["additionalProperties"] is False
        assert set(definition["parameters"]["required"]) == set(
            definition["parameters"].get("properties", {})
        )
        assert "student_id" not in encoded
        assert "owner_user_id" not in encoded
        assert '"pattern"' not in encoded
        assert "institution_id" not in encoded
    assert all(definition["name"] != "run_academic_what_if" for definition in definitions)
    configured = advisor_tool_definitions(include_what_if=True)
    assert len(configured) == 13
    assert any(definition["name"] == "run_academic_what_if" for definition in configured)


@pytest.mark.anyio
async def test_executor_rejects_unknown_and_malformed_arguments_without_running_services() -> None:
    calls: list[object] = []

    async def run_legacy(raw, message):  # type: ignore[no-untyped-def]
        calls.append((raw, message))
        raise AssertionError("must not execute")

    async def load_state(owner):  # type: ignore[no-untyped-def]
        calls.append(owner)
        raise AssertionError("must not load")

    executor = AdvisorToolExecutor(
        owner_user_id="owner-from-auth",
        run_legacy=run_legacy,
        load_state=load_state,
        load_intelligence=None,
    )
    malformed = await executor.execute("get_course_eligibility", '{"student_id":"other"}')
    unknown = await executor.execute("delete_student", "{}")

    assert malformed.output["error"] == "INVALID_ARGUMENTS"
    assert unknown.output["error"] == "UNKNOWN_TOOL"
    assert calls == []
