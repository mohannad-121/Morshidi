import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { InstitutionalDashboard } from "./_components/InstitutionalDashboard";

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api/use-authenticated-api", () => ({ useAuthenticatedApi: () => api }));

const university = "11111111-1111-1111-1111-111111111111";
const metric = (value: number | null, status = "AVAILABLE") => ({
  value, status, unit: "students", inputs: {}, reason_codes: [],
});
const programs = ["AI", "SE", "CS", "CYBER", "MATH", "PHYS", "ARABIC", "ENGLISH",
  "HISTORY", "TRANS", "ECON", "BBA", "ACC", "DJOURN", "RTV", "LAW", "NURS"]
  .map((major, index) => ({
    plan_id: `plan-${index}`, plan_key: `ZU:${index < 4 ? "IT" : "FAC"}:${major}:P12`,
    plan_number: "12", faculty_code: index < 4 ? "IT" : "FAC", faculty_name_ar: "كلية الاختبار",
    major_code: major, major_name_ar: `تخصص ${major}`, student_count: 1,
    data_status: "SUPPRESSED", average_progress_percent: null, average_earned_credits: null,
    median_earned_credits: null, current_registered_credits: 0, blocked_student_count: null,
    review_required_count: null, progress_distribution: [
      { band: "0_24", student_count: null, status: "SUPPRESSED" },
    ], high_demand_courses: [], bottleneck_courses: [],
  }));
const course = {
  course_code: "0200104", name_ar: "مهارات الحاسوب", name_en: "Computer Skills",
  programs: programs.map(item => item.plan_key), requirement_categories: ["UNIVERSITY_REQUIRED"],
  prerequisite_status: "VERIFIED", current_registered: metric(4), eligible_not_registered: metric(8),
  planned_need: metric(6), degree_path_need: metric(9), projected_demand: metric(10),
  projection_confidence: "HIGH", projection_components: { currently_eligible: 8,
    planner_selected: 6, degree_path_upcoming: 9, excluded_completed_or_registered: 4 },
  offered_seats: metric(5), available_seats: metric(1), utilization_percent: metric(80),
  demand_capacity_gap: metric(5), capacity_state: "OVER_DEMAND", bottleneck_score: 78,
  bottleneck_level: "CRITICAL", bottleneck_reasons: ["REQUIRED_CORE_COURSE"],
  affected_student_count: 10, downstream_course_count: 4,
  programs_affected: programs.map(item => item.plan_key),
  action_recommendation: "CONSIDER_ADDITIONAL_SECTION", estimated_students_helped: 5,
  demand_by_program: [],
};
const dashboard = {
  kind: "INSTITUTIONAL_INTELLIGENCE_DASHBOARD", contract_version: "2.0",
  university_id: university, term_key: "CURRENT", role_scope: "INSTITUTION_ADMIN",
  filters: { faculty: null, major: null, plan_key: null }, minimum_cohort_size: 3,
  overview: {
    total_active_students: metric(17), current_registrations: metric(4),
    average_registered_credit_load: { ...metric(3), unit: "credits" },
    eligible_course_opportunities: metric(28), blocked_by_prerequisite: metric(7),
    review_required: metric(2), high_demand_courses: metric(1), capacity_pressure_courses: metric(1),
    academic_bottlenecks: metric(1), approaching_graduation: metric(3), blocked_degree_paths: metric(2),
    students_by_faculty: { IT: 4, FAC: 13 }, students_by_major: { AI: 1 },
  },
  programs, courses: [course], review_queue: [{ course_code: "0300153",
    unresolved_prerequisite_codes: ["0300101"], affected_plans: [programs[0].plan_key],
    affected_student_count: 2, downstream_course_count: 3, system_behavior: "FAIL_CLOSED" }],
  advisor_caseload: { scope: "INSTITUTION", assigned_student_count: null,
    prerequisite_review: 2, blocked_degree_paths: 2, near_graduation: 3,
    registration_conflicts: metric(null, "UNAVAILABLE"), approaching_credit_limit: metric(null, "UNAVAILABLE"),
    without_viable_semester_plan: 2, impacted_by_high_pressure_courses: 10, reason_codes: [] },
  methodology: { projected_demand: "Distinct union", bottleneck_score: "Transparent weighted factors",
    capacity_state: "Configured thresholds", privacy: "Small cohorts suppressed" },
  source_versions: { catalog: "v1", student_state: "v2", offerings: "v3" },
  generated_at: "2026-10-19T00:00:00Z",
};

beforeEach(() => {
  api.request.mockReset();
  api.request.mockImplementation(async (path: string) => new Response(JSON.stringify(
    path.endsWith("/access") ? { scopes: [{ university_id: university, role_scope: "INSTITUTION_ADMIN" }] } :
    path.endsWith("/simulate") ? { simulation_only: true, course_code: "0200104", kind: "ADD_SECTION",
      capacity_before: 5, capacity_after: 35, demand_gap_before: 5, demand_gap_after: -25,
      estimated_students_helped: 5, bottleneck_score_before: 78, bottleneck_score_after: 50,
      affected_programs: [programs[0].plan_key], affected_eligible_students: 8,
      affected_degree_paths: 9, downstream_courses_impacted: 4,
      assumptions: ["SIMULATION_ONLY", "AUTHORITATIVE_DATA_NOT_MUTATED"] } : dashboard), { status: 200 }));
});

test("Arabic overview renders authoritative KPIs and all 17 composite programs", async () => {
  render(<InstitutionalDashboard initialView="overview"/>);
  expect(await screen.findByText("ما الذي يحدث أكاديميًا، ولماذا؟")).toBeTruthy();
  expect(screen.getByText("الذكاء الاصطناعي يشرح؛ القواعد الحتمية تقرر.")).toBeTruthy();
  expect(screen.getByText("الطلبة النشطون")).toBeTruthy();
  expect(screen.getByText("17")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("الكلية"), { target: { value: "IT" } });
  fireEvent.click(screen.getByRole("button", { name: "تحديث" }));
  const dashboardCall = api.request.mock.calls.findLast(call => String(call[0]).includes("/dashboard?"));
  expect(dashboardCall?.[0]).toContain("faculty=IT");
});

test("course table exposes projection components, capacity gap, and deterministic score", async () => {
  render(<InstitutionalDashboard initialView="courses"/>);
  expect(await screen.findByText("ذكاء المواد والطلب")).toBeTruthy();
  expect(screen.getByText("0200104")).toBeTruthy();
  expect(screen.getByText("الطلب يتجاوز الطاقة")).toBeTruthy();
  expect(screen.getByText("78")).toBeTruthy();
  expect(screen.getByText(/مسار قريب 9/)).toBeTruthy();
});

test("what-if is visibly simulation-only and sends a bounded non-mutating request", async () => {
  render(<InstitutionalDashboard initialView="what-if"/>);
  await screen.findByText("محاكاة إضافة شعبة");
  fireEvent.click(screen.getByRole("button", { name: "شغّل المحاكاة" }));
  expect(await screen.findByText("SIMULATION ONLY")).toBeTruthy();
  const call = api.request.mock.calls.find(item => String(item[0]).endsWith("/simulate"));
  expect(call).toBeTruthy();
  const body = JSON.parse((call?.[1] as RequestInit).body as string);
  expect(body).toMatchObject({ course_code: "0200104", kind: "ADD_SECTION", seats: 30 });
  expect(screen.getByText(/AUTHORITATIVE_DATA_NOT_MUTATED/)).toBeTruthy();
});

test("unauthorized institutional access fails closed before showing metrics", async () => {
  api.request.mockRejectedValue(new Error("FORBIDDEN"));
  render(<InstitutionalDashboard initialView="overview"/>);
  expect((await screen.findByRole("alert")).textContent).toContain("مخصصة للمخولين");
  expect(screen.queryByText("الطلبة النشطون")).toBeNull();
});
