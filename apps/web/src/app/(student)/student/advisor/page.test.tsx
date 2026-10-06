import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

process.env.NEXT_PUBLIC_API_BASE_URL = "https://api.morshidi.test";

import AdvisorPage from "@/app/(student)/student/advisor/page";
import { AuthProvider } from "@/auth/auth-provider";
import { FakeAuthClient, fakeSession } from "@/test/fake-auth-client";
import type { AdvisorResponse, ConversationThread } from "@/lib/api/student-types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/student/advisor",
}));

const thread: ConversationThread = {
  id: "11111111-1111-1111-1111-111111111111",
  title: "Academic question",
  status: "ACTIVE",
  created_at: "2026-10-05T08:00:00Z",
  updated_at: "2026-10-05T08:00:00Z",
  last_message_at: null,
  summary_text: null,
};

const advisorResponse = (explanation: string, intent = "GENERAL_CHAT"): AdvisorResponse => ({
  policy_version: "2026-p7",
  intent,
  answer_authority: intent === "GENERAL_CHAT" ? "GENERAL_INFORMATION" : "DETERMINISTIC_RULES_ENGINE",
  clarification: null,
  out_of_scope_reason: null,
  evidence: intent === "GENERAL_CHAT" ? [] : [{
    source: "STUDY_PLAN_RULES",
    course_codes: ["1501211"],
    policy_version: "2026-p7",
  }],
  trace: {
    authoritative_sources: intent === "GENERAL_CHAT" ? [] : ["STUDY_PLAN_12"],
    course_codes: intent === "GENERAL_CHAT" ? [] : ["1501211"],
    policy_versions: [],
    option_references: [],
  },
  result: {},
  explanation,
  explanation_status: "SUCCESS",
  explanation_language: "ar",
});

function renderPage(authClient = new FakeAuthClient(fakeSession())) {
  return render(<AuthProvider client={authClient}><AdvisorPage /></AuthProvider>);
}

function response(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function send(message: string) {
  const user = userEvent.setup();
  const textbox = await screen.findByRole("textbox", { name: "الاستفسار الأكاديمي" });
  await user.type(textbox, message);
  await waitFor(() => expect((screen.getByRole("button", { name: "إرسال" }) as HTMLButtonElement).disabled).toBe(false));
  await user.click(screen.getByRole("button", { name: "إرسال" }));
}

describe("student AI chat resilience", () => {
  let fetchSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    fetchSpy = vi.spyOn(globalThis, "fetch");
  });

  afterEach(() => {
    fetchSpy.mockRestore();
    vi.restoreAllMocks();
  });

  it("loads an empty account and leaves the new-conversation composer ready", async () => {
    fetchSpy.mockResolvedValue(response([]));
    renderPage();

    await screen.findByText("كيف نرسم خطوتك القادمة؟");
    expect((screen.getByRole("textbox", { name: "الاستفسار الأكاديمي" }) as HTMLTextAreaElement).disabled).toBe(false);
    expect(fetchSpy).toHaveBeenCalledWith(
      "https://api.morshidi.test/api/v1/me/conversations?offset=0",
      expect.objectContaining({ cache: "no-store" }),
    );
  });

  it("keeps history failure non-fatal and routes general chat through the student AI endpoint", async () => {
    fetchSpy.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/conversations")) return response({ detail: "unavailable" }, 503);
      if (url.endsWith("/advisor") && init?.method === "POST") {
        return response(advisorResponse("أنا بخير، كيف أقدر أساعدك؟"));
      }
      return response({}, 404);
    });
    renderPage();

    await screen.findByText(/تعذّر مزامنة السجل مؤقتًا/);
    await send("كيفك؟");

    expect(await screen.findByText("أنا بخير، كيف أقدر أساعدك؟")).toBeDefined();
    expect(screen.getByText("كيفك؟")).toBeDefined();
    expect(fetchSpy.mock.calls.some(([url, init]: [RequestInfo | URL, RequestInit?]) =>
      String(url).endsWith("/api/v1/me/advisor") && init?.method === "POST")).toBe(true);
    expect(fetchSpy.mock.calls.some(([url]: [RequestInfo | URL, RequestInit?]) => String(url).includes("/human-advisor"))).toBe(false);
  });

  it("retries history loading without reloading the page", async () => {
    let historyCalls = 0;
    fetchSpy.mockImplementation(async (input: RequestInfo | URL) => {
      if (String(input).includes("/conversations")) {
        historyCalls += 1;
        return historyCalls === 1 ? response({}, 503) : response([]);
      }
      return response({}, 404);
    });
    renderPage();

    await screen.findByText(/تعذّر مزامنة السجل مؤقتًا/);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "إعادة المحاولة" }));

    await screen.findByText("كيف نرسم خطوتك القادمة؟");
    expect(screen.queryByText(/تعذّر مزامنة السجل مؤقتًا/)).toBeNull();
    expect(historyCalls).toBe(2);
  });

  it("uses the same deterministic student endpoint for academic chat when persistence is unavailable", async () => {
    const grounded = "يمكنك تسجيل برمجة كينونية (1501211) وفق نتيجة محرك الأهلية الحتمي.";
    fetchSpy.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/conversations")) return response({}, 503);
      if (url.endsWith("/advisor") && init?.method === "POST") {
        return response(advisorResponse(grounded, "COURSE_RECOMMENDATIONS"));
      }
      return response({}, 404);
    });
    renderPage();

    await screen.findByText(/تعذّر مزامنة السجل مؤقتًا/);
    await send("شو المواد اللي بقدر أسجلها؟");

    expect(await screen.findByText(grounded)).toBeDefined();
    expect(screen.getByText("قواعد الجامعة")).toBeDefined();
  });

  it("creates, continues, and reloads persisted conversation history when storage is available", async () => {
    let created = false;
    fetchSpy.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/conversations?offset=0")) return response(created ? [thread] : []);
      if (url.endsWith("/conversations") && init?.method === "POST") {
        created = true;
        return response(thread, 201);
      }
      if (url.endsWith(`/conversations/${thread.id}/messages`) && init?.method === "POST") {
        return response({
          thread_id: thread.id,
          user_message: { id: "user-1", thread_id: thread.id, role: "USER", content: "مرحبا", message_type: "TEXT", provenance: "USER_STATED", created_at: "2026-10-05T08:01:00Z" },
          assistant_message: { id: "assistant-1", thread_id: thread.id, role: "ASSISTANT", content: "أهلاً بك", message_type: "TEXT", provenance: "GUARDED_PROVIDER", created_at: "2026-10-05T08:01:01Z" },
          advisor: advisorResponse("أهلاً بك"),
        });
      }
      if (url.includes(`/conversations/${thread.id}/messages`)) {
        return response(created ? [
          { id: "user-1", thread_id: thread.id, role: "USER", content: "مرحبا", message_type: "TEXT", provenance: "USER_STATED", created_at: "2026-10-05T08:01:00Z" },
          { id: "assistant-1", thread_id: thread.id, role: "ASSISTANT", content: "أهلاً بك", message_type: "TEXT", provenance: "GUARDED_PROVIDER", created_at: "2026-10-05T08:01:01Z" },
        ] : []);
      }
      return response({}, 404);
    });
    const first = renderPage();
    await screen.findByText("كيف نرسم خطوتك القادمة؟");
    await send("مرحبا");
    expect(await screen.findByText("أهلاً بك")).toBeDefined();

    first.unmount();
    renderPage();
    expect(await screen.findByText("أهلاً بك")).toBeDefined();
    expect(screen.getByText("مرحبا")).toBeDefined();
  });

  it("renders the user message and pending state before the persisted assistant reply, then reconciles without duplication", async () => {
    let finishReply!: (value: Response) => void;
    const pendingReply = new Promise<Response>((resolve) => { finishReply = resolve; });
    fetchSpy.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/conversations?offset=0")) return response([]);
      if (url.endsWith("/conversations") && init?.method === "POST") return response(thread, 201);
      if (url.endsWith(`/conversations/${thread.id}/messages`) && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as { message: string; client_message_id: string };
        expect(body.message).toBe("رسالة فورية");
        expect(body.client_message_id).toMatch(/^[0-9a-f-]{36}$/i);
        return pendingReply;
      }
      return response({}, 404);
    });
    renderPage();
    await screen.findByText("كيف نرسم خطوتك القادمة؟");

    await send("رسالة فورية");

    expect(screen.getByText("رسالة فورية")).toBeDefined();
    expect(screen.getByText("يجهّز مرشدي الرد…")).toBeDefined();
    expect((screen.getByRole("textbox", { name: "الاستفسار الأكاديمي" }) as HTMLTextAreaElement).value).toBe("");

    finishReply(response({
      thread_id: thread.id,
      user_message: { id: "persisted-user", thread_id: thread.id, role: "USER", content: "رسالة فورية", message_type: "TEXT", provenance: "USER_STATED", created_at: "2026-10-05T08:01:00Z" },
      assistant_message: { id: "persisted-assistant", thread_id: thread.id, role: "ASSISTANT", content: "رد محفوظ", message_type: "TEXT", provenance: "DETERMINISTIC_EXPLANATION", created_at: "2026-10-05T08:01:01Z" },
      advisor: advisorResponse("رد محفوظ"),
    }));

    expect(await screen.findByText("رد محفوظ")).toBeDefined();
    expect(screen.getAllByText("رسالة فورية")).toHaveLength(1);
    expect(screen.queryByText("يجهّز مرشدي الرد…")).toBeNull();
  });

  it("shows an authentication-expired state and does not enable sending", async () => {
    fetchSpy.mockResolvedValue(response({ detail: "Authentication is required" }, 401));
    renderPage();

    expect(await screen.findByText("انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى.")).toBeDefined();
    expect((screen.getByRole("button", { name: "إرسال" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows a retryable send error without inventing a response", async () => {
    let advisorCalls = 0;
    fetchSpy.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/conversations")) return response({}, 503);
      if (url.endsWith("/advisor")) {
        advisorCalls += 1;
        return advisorCalls === 1
          ? response({ detail: "provider unavailable" }, 503)
          : response(advisorResponse("استعاد مرشدي الاتصال"));
      }
      return response({}, 404);
    });
    renderPage();
    await screen.findByText(/تعذّر مزامنة السجل مؤقتًا/);
    await send("حاول إرسالها");

    expect(await screen.findByText("تعذّر إرسال الرسالة.")).toBeDefined();
    expect(screen.getByText("حاول إرسالها")).toBeDefined();
    expect(screen.queryByText("استعاد مرشدي الاتصال")).toBeNull();
    const user = userEvent.setup();
    const retries = screen.getAllByRole("button", { name: "إعادة المحاولة" });
    await user.click(retries[retries.length - 1]);
    expect(await screen.findByText("استعاد مرشدي الاتصال")).toBeDefined();
    expect(advisorCalls).toBe(2);
  });

  it("clears pending state on timeout and retries the exact message", async () => {
    const aborted = AbortSignal.abort(new DOMException("timed out", "TimeoutError"));
    vi.spyOn(AbortSignal, "timeout").mockReturnValue(aborted);
    let advisorCalls = 0;
    fetchSpy.mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/conversations")) return response({}, 503);
      if (url.endsWith("/advisor")) {
        advisorCalls += 1;
        if (advisorCalls === 1) throw new DOMException("timed out", "TimeoutError");
        return response(advisorResponse("تم الرد بعد إعادة المحاولة"));
      }
      return response({}, 404);
    });
    renderPage();
    await screen.findByText(/تعذّر مزامنة السجل مؤقتًا/);
    await send("رسالة بطيئة");

    expect(await screen.findByText("استغرق الرد وقتًا أطول من المتوقع.")).toBeDefined();
    expect(screen.queryByText("يجهّز مرشدي الرد…")).toBeNull();
    const user = userEvent.setup();
    const retries = screen.getAllByRole("button", { name: "إعادة المحاولة" });
    await user.click(retries[retries.length - 1]);
    expect(await screen.findByText("تم الرد بعد إعادة المحاولة")).toBeDefined();
    expect(advisorCalls).toBe(2);
  });
});
