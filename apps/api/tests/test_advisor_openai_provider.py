"""Mocked transport tests for the single concrete advisor provider."""

from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from app.advisor.explanation import (
    AdvisorExplanationInput,
    ExplanationFailure,
    ExplanationLanguage,
)
from app.advisor.models import AdvisorIntent, AnswerAuthority
from app.providers.advisor_openai import OPENAI_RESPONSES_URL, OpenAIAdvisorProvider
from app.advisor.conversation_agent import ConversationTurn
from app.advisor.provider import AdvisorInterpretationInput, ProviderFailure, RawAdvisorInterpretation
from app.advisor.provider import UnconfiguredAdvisorLLMProvider
from app.core.config import Settings
from app.main import build_advisor_providers, settings


def _interpretation(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "intent": "COURSE_ELIGIBILITY",
        "general_response": None,
        "course_mentions": [],
        "course_codes_mentioned": ["0300153"],
        "option_references": [],
        "max_credit_hours_per_semester": None,
        "max_courses_per_semester": None,
        "max_semesters_ahead": None,
        "max_paths": None,
        "clarification_hint": None,
        "requested_facets": [],
    }
    value.update(overrides)
    return value


def _response(content: object, *, status: str = "completed") -> httpx.Response:
    text = content if isinstance(content, str) else json.dumps(content)
    return httpx.Response(
        200,
        json={
            "status": status,
            "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}],
        },
    )


@pytest.mark.anyio
async def test_conversation_direct_answer_uses_plain_text_without_interpretation_schema() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return _response("أنا بخير، كيف أقدر أساعدك؟")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAIAdvisorProvider("provider-secret", "test-model", client).converse(
            input_items=[{"role": "user", "content": [{"type": "input_text", "text": "كيفك؟"}]}],
            tools=(),
        )

    assert isinstance(result, ConversationTurn)
    assert result.text == "أنا بخير، كيف أقدر أساعدك؟"
    assert result.tool_calls == ()
    assert captured["tool_choice"] == "auto"
    assert "text" not in captured
    assert "provider-secret" not in json.dumps(captured)


@pytest.mark.anyio
async def test_conversation_parses_multiple_function_calls_and_preserves_output_items() -> None:
    output = [
        {"type": "reasoning", "id": "rs_1", "summary": []},
        {"type": "function_call", "id": "fc_1", "call_id": "call_1", "name": "get_student_intelligence", "arguments": "{}"},
        {"type": "function_call", "id": "fc_2", "call_id": "call_2", "name": "get_course_recommendations", "arguments": "{}"},
    ]

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "completed", "output": output})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAIAdvisorProvider("provider-secret", "test-model", client).converse(
            input_items=[{"role": "user", "content": []}], tools=()
        )

    assert isinstance(result, ConversationTurn)
    assert [call.name for call in result.tool_calls] == [
        "get_student_intelligence", "get_course_recommendations"
    ]
    assert result.output_items == tuple(output)


@pytest.mark.anyio
@pytest.mark.parametrize("payload", [
    {"status": "incomplete", "output": []},
    {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]},
    {"status": "completed", "output": [{"type": "function_call", "call_id": "call", "name": "x", "arguments": None}]},
])
async def test_conversation_incomplete_refusal_and_malformed_calls_are_typed(payload: object) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAIAdvisorProvider("provider-secret", "test-model", client).converse(
            input_items=[], tools=()
        )
    assert isinstance(result, ProviderFailure)


@pytest.mark.anyio
@pytest.mark.parametrize("message", ("هل أستطيع أخذ 0300153؟", "Can I take 0300153?"))
async def test_valid_arabic_and_english_interpretations(message: str) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: _response(_interpretation()))) as client:
        result = await OpenAIAdvisorProvider("provider-secret", "test-model", client).interpret(
            AdvisorInterpretationInput(message)
        )
    assert isinstance(result, RawAdvisorInterpretation)
    assert result.course_codes_mentioned == ("0300153",)


@pytest.mark.anyio
async def test_http_contract_is_structured_secret_safe_and_single_call() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _response(_interpretation())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await OpenAIAdvisorProvider("provider-secret", "test-model", client).interpret(
            AdvisorInterpretationInput("status")
        )
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == OPENAI_RESPONSES_URL
    assert request.headers.get("authorization", "").startswith("Bearer ")
    body = json.loads(request.content)
    assert body["model"] == "test-model" and body["store"] is False
    assert body["text"]["format"]["type"] == "json_schema"
    assert body["text"]["format"]["strict"] is True
    assert body["text"]["format"]["schema"]["additionalProperties"] is False
    assert "authorization" not in body and "student" not in body["input"].casefold()
    assert request.extensions["timeout"]["read"] == 20.0


@pytest.mark.anyio
@pytest.mark.parametrize(
    "content",
    (
        "not-json",
        {"intent": "ACADEMIC_STATUS"},
        _interpretation(decision="ELIGIBLE"),
    ),
)
async def test_malformed_or_academic_decision_fields_are_rejected(content: object) -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: _response(content))) as client:
        result = await OpenAIAdvisorProvider("secret", "model", client).interpret(
            AdvisorInterpretationInput("message")
        )
    assert isinstance(result, ProviderFailure)


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", (400, 429, 500))
async def test_provider_errors_are_typed_without_retry(status_code: int) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code, json={"error": {"message": "private"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAIAdvisorProvider("secret", "model", client).interpret(
            AdvisorInterpretationInput("message")
        )
    assert isinstance(result, ProviderFailure) and calls == 1
    assert "private" not in result.message_key


@pytest.mark.anyio
async def test_timeout_is_typed_and_not_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("private", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAIAdvisorProvider("secret", "model", client).interpret(
            AdvisorInterpretationInput("message")
        )
    assert isinstance(result, ProviderFailure) and result.failure_type.value == "TIMEOUT"
    assert calls == 1


@pytest.mark.anyio
async def test_refusal_or_incomplete_response_is_rejected() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: _response(_interpretation(), status="incomplete"))
    ) as client:
        result = await OpenAIAdvisorProvider("secret", "model", client).interpret(
            AdvisorInterpretationInput("message")
        )
    assert isinstance(result, ProviderFailure)


@pytest.mark.anyio
async def test_explanation_transport_contains_only_minimized_contract() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _response({"text": "Grounded result.", "language": "en"})

    value = AdvisorExplanationInput(
        "Explain status",
        AdvisorIntent.ACADEMIC_STATUS,
        AnswerAuthority.DETERMINISTIC,
        "{}",
        (),
        ("authority=DETERMINISTIC",),
        ExplanationLanguage.ENGLISH,
        (),
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await OpenAIAdvisorProvider("transport-only-secret", "model", client).explain(value)
    assert not isinstance(result, ExplanationFailure)
    body = json.loads(requests[0].content)
    serialized = json.dumps(body).casefold()
    for forbidden in ("owner_user_id", "supabase", "chain_of_thought", "transport-only-secret"):
        assert forbidden not in serialized
    assert body["store"] is False


@pytest.mark.parametrize("key,model", (("", "model"), ("secret", ""), (" ", "model")))
def test_invalid_configuration_is_rejected(key: str, model: str) -> None:
    with pytest.raises(ValueError):
        OpenAIAdvisorProvider(key, model, object())  # type: ignore[arg-type]


def test_settings_load_missing_and_complete_provider_configuration() -> None:
    missing = Settings(_env_file=None)  # type: ignore[call-arg]
    configured = Settings(
        _env_file=None,  # type: ignore[call-arg]
        advisor_llm_api_key=SecretStr("not-a-real-key"),
        advisor_llm_model="configured-model",
    )
    assert missing.advisor_llm_api_key is None and missing.advisor_llm_model is None
    assert configured.advisor_llm_api_key is not None
    assert configured.advisor_llm_api_key.get_secret_value() == "not-a-real-key"


def test_production_wiring_requires_both_key_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    client = object()
    monkeypatch.setattr(settings, "advisor_llm_api_key", None)
    monkeypatch.setattr(settings, "advisor_llm_model", "model")
    interpretation, explanation = build_advisor_providers(client)  # type: ignore[arg-type]
    assert isinstance(interpretation, UnconfiguredAdvisorLLMProvider)
    assert explanation is None

    monkeypatch.setattr(settings, "advisor_llm_api_key", SecretStr("secret"))
    monkeypatch.setattr(settings, "advisor_llm_model", " ")
    interpretation, explanation = build_advisor_providers(client)  # type: ignore[arg-type]
    assert isinstance(interpretation, UnconfiguredAdvisorLLMProvider)
    assert explanation is None

    monkeypatch.setattr(settings, "advisor_llm_model", "model")
    interpretation, explanation = build_advisor_providers(client)  # type: ignore[arg-type]
    assert isinstance(interpretation, OpenAIAdvisorProvider)
    assert explanation is interpretation
