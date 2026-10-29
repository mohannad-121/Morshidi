import { describe, expect, it, vi, beforeEach } from "vitest";
import { AuthenticatedApiClient } from "@/lib/api/authenticated-client";
import { VoiceApiService } from "./voice-api";

beforeEach(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
});

describe("VoiceApiService", () => {
  const fakeTokens = {
    getAccessToken: vi.fn().mockResolvedValue("mock-jwt-token"),
    refreshAccessToken: vi.fn().mockResolvedValue("mock-jwt-token"),
    invalidateSession: vi.fn().mockResolvedValue(undefined),
  };

  it("fetches voice status successfully", async () => {
    const fakeFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        enabled: true,
        configured: true,
        model: "gpt-live-1",
        voice: "coral",
        max_duration_seconds: 900,
        remaining_daily_quota: 25,
        daily_usage: 0,
      }),
    });

    const client = new AuthenticatedApiClient(fakeTokens, fakeFetch as unknown as typeof fetch, "http://localhost:8000");
    const service = new VoiceApiService(client);

    const status = await service.getStatus();
    expect(status.enabled).toBe(true);
    expect(status.configured).toBe(true);
    expect(status.voice).toBe("coral");
    expect(status.remaining_daily_quota).toBe(25);
  });

  it("creates a gpt-live-1 session with server-mediated SDP answer", async () => {
    const fakeFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        session_id: "sess_test_123",
        sdp_answer: "v=0\r\no=OpenAI ...",
        model: "gpt-live-1",
        voice: "alloy",
        endpoint_type: "live",
        max_duration_seconds: 900,
        default_language: "ar",
        default_dialect: "msa",
        tools: ["get_remaining_requirements"],
        university_id: "uni-hash-1",
      }),
    });

    const client = new AuthenticatedApiClient(fakeTokens, fakeFetch as unknown as typeof fetch, "http://localhost:8000");
    const service = new VoiceApiService(client);

    const session = await service.createSession({
      thread_id: "thread-456",
      sdp_offer: "v=0\r\no=Browser ...",
    });
    expect(session.session_id).toBe("sess_test_123");
    expect(session.sdp_answer).toBe("v=0\r\no=OpenAI ...");
    expect(session.endpoint_type).toBe("live");
    expect(session.default_dialect).toBe("msa");
    expect(session.tools).toContain("get_remaining_requirements");
  });

  it("executes delegated academic tool on the backend with concise summary", async () => {
    const fakeFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        call_id: "call_req_1",
        tool_name: "get_remaining_requirements",
        output: { ok: true, remaining_credit_hours: 12 },
        summary_text: "بحسب خطتك الدراسية المعتمدة، يتبقى عليك 12 ساعة معتمدة.",
        ok: true,
      }),
    });

    const client = new AuthenticatedApiClient(fakeTokens, fakeFetch as unknown as typeof fetch, "http://localhost:8000");
    const service = new VoiceApiService(client);

    const response = await service.delegateTool({
      call_id: "call_req_1",
      tool_name: "get_remaining_requirements",
      arguments: "{}",
      user_transcript: "كم باقيلي ساعات للتخرج؟",
    });

    expect(response.ok).toBe(true);
    expect(response.call_id).toBe("call_req_1");
    expect((response.output as { remaining_credit_hours: number }).remaining_credit_hours).toBe(12);
    expect(response.summary_text).toContain("12 ساعة");
  });

  it("terminates session and reconciles actual duration in seconds", async () => {
    const fakeFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ ok: true }),
    });

    const client = new AuthenticatedApiClient(fakeTokens, fakeFetch as unknown as typeof fetch, "http://localhost:8000");
    const service = new VoiceApiService(client);

    await service.endSession("sess_test_123", 45.2);

    expect(fakeFetch).toHaveBeenCalledTimes(1);
    const bodySent = JSON.parse(fakeFetch.mock.calls[0][1].body);
    expect(bodySent.session_id).toBe("sess_test_123");
    expect(bodySent.actual_duration_seconds).toBe(45.2);
  });

  it("syncs speech turns into student conversation thread", async () => {
    const fakeFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        synced: true,
        user_message_id: "usr-msg-1",
        assistant_message_id: "asst-msg-2",
      }),
    });

    const client = new AuthenticatedApiClient(fakeTokens, fakeFetch as unknown as typeof fetch, "http://localhost:8000");
    const service = new VoiceApiService(client);

    const res = await service.syncTurn({
      thread_id: "thread-123",
      user_transcript: "كم ساعة متبقية للتخرج؟",
      assistant_transcript: "متبقي عليك 12 ساعة معتمدة.",
      client_turn_id: "turn-abc",
    });

    expect(res.synced).toBe(true);
  });
});
