import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import DiagnosticPage from "./page";

const client = { request: vi.fn() };
vi.mock("@/lib/api/use-authenticated-api", () => ({ useAuthenticatedApi: () => client }));

const session = { session_id: "session-1", status: "IN_PROGRESS", assessment_version: "QUICK_DIAGNOSTIC_V1",
  answered_count: 0, maximum_questions: 16, question: { question_id: "P01", assessment_version: "QUICK_DIAGNOSTIC_V1",
    domain: "PROGRAMMING_REASONING", prompt_ar: "ما الناتج؟", prompt_en: "What is the output?",
    options: [{ option_id: "A", text_ar: "الإجابة أ", text_en: "A" }] } };

beforeEach(() => { client.request.mockReset(); });

test("resumes an active RTL diagnostic and submits only question and option", async () => {
  client.request
    .mockResolvedValueOnce(new Response(JSON.stringify({ active_session_id: "session-1" })))
    .mockResolvedValueOnce(new Response(JSON.stringify(session)))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...session, answered_count: 1 })));
  render(<DiagnosticPage />);
  await screen.findByRole("heading", { name: "ما الناتج؟" });
  expect(document.querySelector("main[dir='rtl']")).toBeTruthy();
  expect(screen.getByRole("link", { name: "إكماله لاحقاً" }).getAttribute("href")).toBe("/student");
  fireEvent.click(screen.getByRole("button", { name: /الإجابة أ/ }));
  await waitFor(() => expect(client.request).toHaveBeenLastCalledWith("/api/v1/me/diagnostic/session-1/answer", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: "P01", selected_option: "A" }),
  }));
});

test("shows the completion state", async () => {
  client.request
    .mockResolvedValueOnce(new Response(JSON.stringify({ active_session_id: "session-1" })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ ...session, status: "COMPLETED", question: null })));
  render(<DiagnosticPage />);
  expect(await screen.findByRole("heading", { name: "بصمتك الأكاديمية جاهزة" })).toBeTruthy();
});
