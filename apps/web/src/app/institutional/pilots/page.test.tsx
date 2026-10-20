import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import PilotsDashboardPage from "./page";

// Mock auth client
const api = vi.hoisted(() => ({ request: vi.fn(), fetch: vi.fn() }));
vi.mock("@/lib/api/use-authenticated-api", () => ({ useAuthenticatedApi: () => api }));

// Mock institutional integrations for listTenants
vi.mock("@/lib/api/institutional-integrations", () => ({
  listTenants: vi.fn().mockResolvedValue([
    {
      id: "10000000-0000-0000-0000-000000000001",
      tenant_key: "zarqa",
      name_ar: "جامعة الزرقاء",
      name_en: "Zarqa University",
      country: "Jordan",
      timezone: "Asia/Amman",
      default_locale: "ar",
      status: "ACTIVE",
      active: true,
    },
  ]),
}));

// Mock institutional pilots
vi.mock("@/lib/api/institutional-pilots", () => ({
  listPilots: vi.fn().mockResolvedValue([
    {
      id: "pilot-1234-5678",
      university_id: "10000000-0000-0000-0000-000000000001",
      pilot_name: "الإطلاق التجريبي لكلية تكنولوجيا المعلومات",
      status: "READ_ONLY_PILOT_ACTIVE",
      mode: "READ_ONLY_PILOT",
      target_start_date: "2026-03-01",
      target_end_date: "2026-06-30",
      cohort_scope: {
        faculties: ["كلية تكنولوجيا المعلومات"],
        majors: ["علم الحاسوب", "هندسة البرمجيات"],
        academic_plans: ["2023"],
        target_terms: ["20252"],
        estimated_student_count: 120,
        scope_notes: "عينة تجريبية أولى منضبطة",
      },
      discovery_intake: {
        university_name_official: "جامعة الزرقاء",
        country: "Jordan",
        timezone: "Asia/Amman",
        preferred_locale: "ar",
        sis_vendor: "FakeUniversity / Sandbox",
        hosting_model: "CLOUD",
        api_available: true,
        api_version: "v1",
        sandbox_available: true,
        documentation_available: true,
        identity_protocol: "OIDC",
        academic_structure_summary: "فصول وساعات معتمدة",
        network_restrictions: "IP Whitelisting required",
        notes: "بيئة تجريبية للاختبار",
      },
      technical_questionnaire: {},
      security_questionnaire: {},
      notes: "مشروع إطلاق تحت الإشراف",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ]),
  createPilot: vi.fn().mockImplementation((_api, payload) =>
    Promise.resolve({
      id: "pilot-new-9999",
      university_id: payload.university_id,
      pilot_name: payload.pilot_name,
      status: "DRAFT",
      mode: payload.mode || "READ_ONLY_PILOT",
      cohort_scope: payload.cohort_scope || { faculties: [], majors: [], estimated_student_count: 50 },
      discovery_intake: payload.discovery_intake || {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  ),
}));

test("renders pilots dashboard with metrics and pilot list", async () => {
  render(<PilotsDashboardPage />);

  // Title and header check
  expect(screen.getByText("نظام إطلاق الجامعات التجريبي (Pilot Onboarding)")).toBeDefined();

  // Wait for pilots to load
  await waitFor(() => {
    expect(screen.getByText("الإطلاق التجريبي لكلية تكنولوجيا المعلومات")).toBeDefined();
  });

  // Check metrics cards
  expect(screen.getByText("إجمالي المشاريع")).toBeDefined();
  expect(screen.getByText("مشاريع نشطة")).toBeDefined();

  // Check pilot card badges and details
  expect(screen.getAllByText("إطلاق تجريبي نشط (قراءة)").length).toBeGreaterThanOrEqual(1);
  expect(screen.getByText("قراءة فقط (آمن)")).toBeDefined();
  expect(screen.getByText("120 طالب")).toBeDefined();

  // Check downloadable toolkit section
  expect(screen.getByText("حزمة الإطلاق وقوالب التهيئة الرسمية (Pilot Toolkit & Templates)")).toBeDefined();
  expect(screen.getByText("استبيان استكشاف نظم الجامعة (IT Discovery)")).toBeDefined();
  expect(screen.getByText("قالب مطابقة المواد والشُعب (Course Mapping)")).toBeDefined();
  expect(screen.getByText("استبيان الأمن وحماية البيانات (Security Questionnaire)")).toBeDefined();
});

test("can open and submit new pilot modal", async () => {
  render(<PilotsDashboardPage />);

  // Open create modal
  const createBtn = screen.getByRole("button", { name: /مشروع إطلاق جديد/ });
  fireEvent.click(createBtn);

  // Check modal opened
  await waitFor(() => {
    expect(screen.getByText("إنشاء مشروع إطلاق تجريبي جديد")).toBeDefined();
  });

  // Fill in name
  const nameInput = screen.getByPlaceholderText(/الإطلاق التجريبي لكليات الهندسة/);
  fireEvent.change(nameInput, { target: { value: "مشروع كلية التمريض 2026" } });

  // Submit modal
  const submitBtn = screen.getByRole("button", { name: "إنشاء المشروع" });
  fireEvent.click(submitBtn);

  await waitFor(() => {
    expect(screen.getByText("مشروع كلية التمريض 2026")).toBeDefined();
  });
});
