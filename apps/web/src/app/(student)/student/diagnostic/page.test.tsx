import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import DiagnosticPage from "./page";

const client = { request: vi.fn() };
vi.mock("@/lib/api/use-authenticated-api", () => ({ useAuthenticatedApi: () => client }));

const session = { session_id: "session-1", status: "IN_PROGRESS", assessment_version: "QUICK_DIAGNOSTIC_V2",
  answered_count: 0, maximum_questions: 30, question: { question_id: "P01", assessment_version: "QUICK_DIAGNOSTIC_V2",
    prompt_ar: "ما الناتج؟", prompt_en: "What is the output?",
    options: [{ option_id: "A", text_ar: "الإجابة أ", text_en: "A" }] } };

beforeEach(() => { client.request.mockReset(); });

test("resumes an active RTL diagnostic and submits only question and option", async () => {
  client.request
    .mockResolvedValueOnce(new Response(JSON.stringify({ active_session_id: "session-1" })))
    .mockResolvedValueOnce(new Response(JSON.stringify(session)))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...session, answered_count: 1 })));
  render(<DiagnosticPage />);
  await screen.findByRole("heading", { name: "ما الناتج؟" });
  expect(client.request.mock.calls[0]?.[0]).toBe(
    "/api/v1/me/diagnostic/status?assessment_version=QUICK_DIAGNOSTIC_V2",
  );
  expect(document.querySelector("main[dir='rtl']")).toBeTruthy();
  expect(screen.getByRole("link", { name: "إكماله لاحقاً" }).getAttribute("href")).toBe("/student");
  fireEvent.click(screen.getByRole("button", { name: /الإجابة أ/ }));
  fireEvent.click(screen.getByRole("button", { name: /متوسطة/ }));
  fireEvent.click(screen.getByRole("button", { name: "السؤال التالي" }));
  await waitFor(() => expect(client.request).toHaveBeenLastCalledWith("/api/v1/me/diagnostic/session-1/answer", {
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
    .mockResolvedValueOnce(new Response(JSON.stringify(session)));
  render(<DiagnosticPage />);
  await waitFor(() => expect(client.request).toHaveBeenCalledTimes(2));
  expect(client.request.mock.calls[1]?.[0]).toBe(
    "/api/v1/me/diagnostic/start?assessment_version=QUICK_DIAGNOSTIC_V2",
  );
});

test("shows the completion state", async () => {
  client.request
    .mockResolvedValueOnce(new Response(JSON.stringify({ active_session_id: "session-1" })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...session, status: "COMPLETED", answered_count: 30, question: null })));
  render(<DiagnosticPage />);
  expect(await screen.findByRole("heading", { name: "خط الأساس الأكاديمي جاهز" })).toBeTruthy();
  expect(screen.getByText("اكتملت 30 من 30")).toBeTruthy();
});
