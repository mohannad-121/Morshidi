import { render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import StudentIntelligencePage from "./page";

const client = { request: vi.fn() };
vi.mock("@/lib/api/use-authenticated-api", () => ({ useAuthenticatedApi: () => client }));

const example = {
  student_id: "profile-1", institution_id: "institution-1", study_plan_id: "plan-12",
  intelligence_model_version: "STUDENT_INTELLIGENCE_PROFILE_V2",
  taxonomy_version: "MORSHIDI_SKILL_TAXONOMY_V2", fusion_policy_version: "EVIDENCE_FUSION_V1",
  generated_at: "2026-10-11T12:00:00Z", source_snapshot_version: "abc",
  cumulative_gpa: null, gpa_scale: null, earned_credits: 0, verified_grade_count: 0,
  completed_course_count: 0, failed_course_count: 0, repeated_course_count: 0,
  current_course_count: 0, academic_progress_band: "NEW", performance_trend: "INSUFFICIENT_EVIDENCE",
  evidence_quality: "INSUFFICIENT", cold_start_status: "COLD_START_NO_PERFORMANCE_EVIDENCE",
  diagnostic_recommended: true, diagnostic_completed: false, latest_assessment_version: null,
  latest_completed_at: null, strengths: [], development_areas: [], preferences: {},
  skills: [{ skill_id: "PROGRAMMING", score: 82, confidence: "MEDIUM",
    evidence_quality: "MODELED_DIAGNOSTIC", university_evidence_count: 0,
    diagnostic_evidence_count: 1, contributing_courses: [],
    contributing_question_domains: ["PROGRAMMING_REASONING"],
    source_types: ["COMPLETED_QUICK_DIAGNOSTIC"], reason_codes: ["DIAGNOSTIC_BASELINE_ONLY"] }],
  limitations: ["Modeled intelligence is not an official university evaluation."],
};

beforeEach(() => {
  client.request.mockReset();
  client.request.mockResolvedValue(new Response(JSON.stringify(example)));
});

test("Arabic RTL cold-start view offers a non-blocking diagnostic and evidence labels", async () => {
  render(<StudentIntelligencePage />);
  expect(screen.getByRole("status").textContent).toContain("بناء");
  await screen.findByRole("heading", { name: "بصمتي الأكاديمية" });
  expect(document.querySelector("main[dir='rtl']")).toBeTruthy();
  expect(screen.getByText("خلّينا نتعرّف عليك")).toBeTruthy();
  expect(screen.getByRole("link", { name: "ابدأ الاختبار السريع" }).getAttribute("href")).toBe("/student/diagnostic");
  expect(screen.getByText("البرمجة")).toBeTruthy();
  expect(screen.getByText(/جامعة: 0 · تشخيص: 1/)).toBeTruthy();
  expect(client.request).toHaveBeenCalledWith("/api/v1/me/student-intelligence", { cache: "no-store" });
});

test("established evidence removes the onboarding prompt", async () => {
  client.request.mockResolvedValueOnce(new Response(JSON.stringify({
    ...example, verified_grade_count: 8, evidence_quality: "AUTHORITATIVE",
    cold_start_status: "ESTABLISHED_ACADEMIC_EVIDENCE", diagnostic_recommended: false,
  })));
  render(<StudentIntelligencePage />);
  await screen.findByRole("heading", { name: "بصمتي الأكاديمية" });
  expect(screen.queryByText("خلّينا نتعرّف عليك")).toBeNull();
  expect(screen.getByText(/8 علامة جامعية موثقة/)).toBeTruthy();
});

test("completed cold-start diagnostic is separated from official evidence", async () => {
  client.request.mockResolvedValueOnce(new Response(JSON.stringify({
    ...example, diagnostic_recommended: false, diagnostic_completed: true,
    latest_assessment_version: "QUICK_DIAGNOSTIC_V2",
  })));
  render(<StudentIntelligencePage />);
  await screen.findByRole("heading", { name: "بصمتي الأكاديمية" });
  expect(screen.getByText("أدلة الجامعة الرسمية")).toBeTruthy();
  expect(screen.getByText("أدلة التشخيص")).toBeTruthy();
  expect(screen.getByText(/هذا تقييم أولي وسيتحدّث تلقائياً/)).toBeTruthy();
  expect(screen.getByText("30")).toBeTruthy();
  expect(screen.getByText(/إجابة مكتملة/)).toBeTruthy();
});

test("error state is explicit", async () => {
  client.request.mockRejectedValueOnce(new Error("offline"));
  render(<StudentIntelligencePage />);
  expect(await screen.findByRole("alert")).toBeTruthy();
});
