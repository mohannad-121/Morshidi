# Conversational Advisor Provider and Grounded Tools

## Production boundary

Morshidi uses the server-side OpenAI Responses API as a conversational orchestration layer. The configured model may answer harmless general questions directly or request one or more allowlisted read-only tools. It never receives an API key in application input, and browser code never calls OpenAI directly.

The architectural rule remains: **AI explains; deterministic rules decide.** OpenAI understands language, resolves conversational references, chooses tools, combines results, and writes the final response. Existing Morshidi engines remain authoritative for eligibility, prerequisites, progress, recommendations, semester plans, degree paths, Student Intelligence evidence, and What-If simulation.

## Bounded tool loop

`advisor/conversation_agent.py` implements at most five provider rounds:

1. send the current message, bounded recent context, system instruction, and tool definitions;
2. accept either ordinary output text or any number of `function_call` output items;
3. execute independent read-only calls concurrently;
4. append the original response output items and matching `function_call_output` items;
5. ask the model for a final answer or another bounded tool round.

The original output items are retained between stateless `store: false` requests so Responses API reasoning/function-call items remain linked. No raw chain-of-thought is extracted or persisted. Safe internal metadata is limited to called tool names, authoritative/modeled sources represented by deterministic results, and limitations.

## Tool registry and identity

`advisor/tool_registry.py` publishes strict JSON Schemas for student academic summary/progress, bounded Student Intelligence V2, course eligibility/eligible courses/recommendations/information/comparison, remaining requirements, semester plans, degree paths, current enrollments, and ephemeral What-If when its existing context loader is configured.

The schemas never contain `student_id`, `owner_user_id`, or `institution_id`. `advisor/tool_executor.py` receives the authenticated owner from `AdvisorService`, validates every model argument with Pydantic, rejects unknown fields/tools, and then calls existing services and engines. The What-If adapter receives an internally constructed self-service authorization context and has no persistence operation.

Student Intelligence is projected through the bounded V2 advisor contract. It contains scores, confidence, evidence counts, reasoning patterns, and limitations, but never diagnostic answers, answer keys, question payloads, or scoring internals.

## Conversation and general knowledge

The instruction supports Jordanian/Levantine Arabic, Modern Standard Arabic, English, mixed language, misspellings, follow-ups, pronouns, and multi-part requests. Bounded owner-scoped context is supplied only for reference resolution and user-stated preferences; it is explicitly marked untrusted and cannot replace current academic facts.

General conversation and educational concepts require one provider call and no academic load. Student-specific claims require tools. Multiple clauses may produce multiple tool calls in one round. Internal reason/evidence codes must be translated into natural language rather than copied to the student.

## Compatibility and fallback

`RawAdvisorInterpretation`, `AdvisorIntent`, the strict interpretation schema, and the deterministic pre-router remain for legacy providers, compatibility tests, and safe deterministic fallback. They are not a prerequisite for configured OpenAI conversation. A normal message therefore cannot fail merely because one large intent object was malformed.

If OpenAI times out or is unavailable, an obvious deterministic request may use the existing pre-router and engine. Open-ended requests return a friendly temporary message without invented facts. The existing public `AdvisorResponse` contract is preserved; one deterministic result remains its primary structured payload while the natural answer may combine several tool results.

## Provider response handling

The adapter recognizes multiple Responses API output items, including messages, output text, reasoning items carried forward opaquely, and multiple function calls. It treats incomplete responses, refusals, malformed calls, empty completed responses, timeout, rate limits, 4xx, and 5xx as typed safe failures. Provider payloads, request IDs, usage, credentials, prompts, and hidden reasoning never enter student responses or logs.

The older strict JSON interpretation and explanation methods remain intact for compatibility. The conversational final answer is ordinary text and is not forced through the old interpretation schema.
