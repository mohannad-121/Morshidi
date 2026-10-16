import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import DiagnosticPage from "./page";

const client = { request: vi.fn() };
vi.mock("@/lib/api/use-authenticated-api", () => ({ useAuthenticatedApi: () => client }));

const v2Session = { session_id: "session-v2", status: "IN_PROGRESS", assessment_version: "QUICK_DIAGNOSTIC_V2",
  answered_count: 0, maximum_questions: 30, question: { question_id: "P01", assessment_version: "QUICK_DIAGNOSTIC_V2",
    prompt_ar: "ما الناتج؟", prompt_en: "What is the output?",
    options: [{ option_id: "A", text_ar: "الإجابة أ", text_en: "A" }] } };
const v1Session = { ...v2Session, session_id: "session-v1", assessment_version: "QUICK_DIAGNOSTIC_V1",
  maximum_questions: 16, question: { ...v2Session.question, assessment_version: "QUICK_DIAGNOSTIC_V1" } };

beforeEach(() => { client.request.mockReset(); });

function mockActiveSession(session: typeof v2Session) {
  client.request
    .mockResolvedValueOnce(new Response(JSON.stringify({ active_session_id: session.session_id })))
    .mockResolvedValueOnce(new Response(JSON.stringify(session)));
}

test("shows the legacy transition screen without presenting V1 as 1 of 30", async () => {
  mockActiveSession(v1Session);
  render(<DiagnosticPage />);
  expect(await screen.findByRole("heading", { name: "لديك تشخيص قديم غير مكتمل" })).toBeTruthy();
  expect(screen.getByText("بدأت نسخة سابقة من التشخيص. يمكنك إكمالها، أو إغلاقها والبدء بالتشخيص الجديد المكوّن من 30 سؤالاً.")).toBeTruthy();
  expect(screen.getByRole("button", { name: "إكمال التشخيص القديم" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "ابدأ التشخيص الجديد — 30 سؤال" })).toBeTruthy();
  expect(screen.queryByText("السؤال 1 من 30")).toBeNull();
});

test("continues V1 with its maximum and the old answer shape without confidence or timing", async () => {
  mockActiveSession(v1Session);
  client.request.mockResolvedValueOnce(new Response(JSON.stringify({ ...v1Session, answered_count: 1 })));
  render(<DiagnosticPage />);
  fireEvent.click(await screen.findByRole("button", { name: "إكمال التشخيص القديم" }));
  expect(await screen.findByRole("heading", { name: "ما الناتج؟" })).toBeTruthy();
  expect(screen.getByRole("heading", { name: "السؤال 1 من 16" })).toBeTruthy();
  expect(screen.getByRole("progressbar").getAttribute("aria-valuemax")).toBe("16");
  expect(screen.queryByText("ما مدى ثقتك بإجابتك؟")).toBeNull();
  expect(screen.queryByRole("button", { name: /متوسطة/ })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /الإجابة أ/ }));
  fireEvent.click(screen.getByRole("button", { name: "السؤال التالي" }));
  await waitFor(() => expect(client.request).toHaveBeenLastCalledWith("/api/v1/me/diagnostic/session-v1/answer", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: "P01", selected_option: "A" }),
  }));
});

test("keeps the V2 confidence selector hidden after choosing to continue V1", async () => {
  mockActiveSession(v1Session);
  render(<DiagnosticPage />);
  fireEvent.click(await screen.findByRole("button", { name: "إكمال التشخيص القديم" }));
  await screen.findByRole("heading", { name: "ما الناتج؟" });
  expect(screen.queryByText("ما مدى ثقتك بإجابتك؟")).toBeNull();
  expect(screen.queryByRole("button", { name: /منخفضة|متوسطة|مرتفعة/ })).toBeNull();
});

test("derives the counter and progress bar from session.maximum_questions", async () => {
  mockActiveSession({ ...v1Session, answered_count: 3 });
  render(<DiagnosticPage />);
  fireEvent.click(await screen.findByRole("button", { name: "إكمال التشخيص القديم" }));
  expect(await screen.findByRole("heading", { name: "السؤال 4 من 16" })).toBeTruthy();
  const progress = screen.getByRole("progressbar");
  expect(progress.getAttribute("aria-valuemax")).toBe("16");
  expect(progress.firstElementChild?.getAttribute("style")).toContain("width: 19%");
});

test("abandons V1 before starting V2 and renders the returned V2 evidence UI", async () => {
  let resolveAbandon!: (value: Response) => void;
  const pendingAbandon = new Promise<Response>(resolve => { resolveAbandon = resolve; });
  mockActiveSession(v1Session);
  client.request
    .mockReturnValueOnce(pendingAbandon)
    .mockResolvedValueOnce(new Response(JSON.stringify(v2Session)));
  render(<DiagnosticPage />);
  fireEvent.click(await screen.findByRole("button", { name: "ابدأ التشخيص الجديد — 30 سؤال" }));
  await waitFor(() => expect(client.request).toHaveBeenCalledTimes(3));
  expect(client.request.mock.calls[2]).toEqual([
    "/api/v1/me/diagnostic/session-v1/abandon", { method: "POST" },
  ]);
  expect(client.request.mock.calls.some(call => call[0] === "/api/v1/me/diagnostic/start?assessment_version=QUICK_DIAGNOSTIC_V2")).toBe(false);
  await act(async () => { resolveAbandon(new Response(null, { status: 204 })); });
  await waitFor(() => expect(client.request).toHaveBeenCalledTimes(4));
  expect(client.request.mock.calls[3]?.[0]).toBe(
    "/api/v1/me/diagnostic/start?assessment_version=QUICK_DIAGNOSTIC_V2",
  );
  expect(await screen.findByRole("heading", { name: "السؤال 1 من 30" })).toBeTruthy();
  expect(screen.getByText("ما مدى ثقتك بإجابتك؟")).toBeTruthy();
});

test("does not start V2 when abandoning the V1 session fails", async () => {
  mockActiveSession(v1Session);
  client.request.mockResolvedValueOnce(new Response(null, { status: 500 }));
  render(<DiagnosticPage />);
  fireEvent.click(await screen.findByRole("button", { name: "ابدأ التشخيص الجديد — 30 سؤال" }));
  expect((await screen.findByRole("alert")).textContent).toContain("تعذّر إغلاق التشخيص القديم");
  expect(client.request).toHaveBeenCalledTimes(3);
  expect(client.request.mock.calls.some(call => call[0] === "/api/v1/me/diagnostic/start?assessment_version=QUICK_DIAGNOSTIC_V2")).toBe(false);
  expect(screen.getByRole("heading", { name: "لديك تشخيص قديم غير مكتمل" })).toBeTruthy();
});

test("resumes V2 with 1 of 30, confidence, timing, and the V2 answer shape", async () => {
  mockActiveSession(v2Session);
  client.request.mockResolvedValueOnce(new Response(JSON.stringify({ ...v2Session, answered_count: 1 })));
  render(<DiagnosticPage />);
  await screen.findByRole("heading", { name: "ما الناتج؟" });
  expect(client.request.mock.calls[0]?.[0]).toBe(
    "/api/v1/me/diagnostic/status?assessment_version=QUICK_DIAGNOSTIC_V2",
  );
  expect(screen.getByRole("heading", { name: "السؤال 1 من 30" })).toBeTruthy();
  expect(screen.getByRole("progressbar").getAttribute("aria-valuemax")).toBe("30");
  expect(screen.getByText("ما مدى ثقتك بإجابتك؟")).toBeTruthy();
  expect(document.querySelector("main[dir='rtl']")).toBeTruthy();
  expect(screen.getByRole("link", { name: "إكماله لاحقاً" }).getAttribute("href")).toBe("/student");
  fireEvent.click(screen.getByRole("button", { name: /الإجابة أ/ }));
  fireEvent.click(screen.getByRole("button", { name: /متوسطة/ }));
  fireEvent.click(screen.getByRole("button", { name: "السؤال التالي" }));
  await waitFor(() => expect(client.request).toHaveBeenLastCalledWith("/api/v1/me/diagnostic/session-v2/answer", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: expect.stringContaining('"self_confidence":"MEDIUM"'),
  }));
  const request = client.request.mock.calls.at(-1)?.[1] as { body: string };
  expect(JSON.parse(request.body)).toMatchObject({ question_id: "P01", selected_option: "A",
    self_confidence: "MEDIUM" });
  expect(JSON.parse(request.body).response_time_ms).toEqual(expect.any(Number));
  expect(screen.queryByText("PROGRAMMING REASONING")).toBeNull();
});

test("explicitly opts new sessions into the V2 rollout contract", async () => {
  client.request
    .mockResolvedValueOnce(new Response(JSON.stringify({ active_session_id: null })))
    .mockResolvedValueOnce(new Response(JSON.stringify(v2Session)));
  render(<DiagnosticPage />);
  await waitFor(() => expect(client.request).toHaveBeenCalledTimes(2));
  expect(client.request.mock.calls[1]?.[0]).toBe(
    "/api/v1/me/diagnostic/start?assessment_version=QUICK_DIAGNOSTIC_V2",
  );
});

test("uses maximum_questions for the V2 final-question action", async () => {
  mockActiveSession({ ...v2Session, answered_count: 29 });
  render(<DiagnosticPage />);
  expect(await screen.findByRole("heading", { name: "السؤال 30 من 30" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "إنهاء التشخيص" }).hasAttribute("disabled")).toBe(true);
});

test("uses the stored maximum in a completed legacy label without V2 evidence language", async () => {
  mockActiveSession({ ...v1Session, status: "COMPLETED", answered_count: 12, question: null } as unknown as typeof v2Session);
  render(<DiagnosticPage />);
  expect(await screen.findByRole("heading", { name: "اكتمل التشخيص القديم" })).toBeTruthy();
  expect(screen.getByText("اكتملت 12 من 16")).toBeTruthy();
  expect(screen.queryByText(/وقت الاستجابة/)).toBeNull();
});
