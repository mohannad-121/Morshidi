import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import IntegrationsDashboardPage from "./page";

// Mock auth and API client
const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api/use-authenticated-api", () => ({ useAuthenticatedApi: () => api }));

// Mock API module
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
  getConfig: vi.fn().mockResolvedValue({
    university_id: "10000000-0000-0000-0000-000000000001",
    provider_type: "fake_university",
    base_url: "https://fake-university-aqdn.onrender.com",
    auth_method: "token",
    secret_env_ref: "UNI_SERVICE_KEY",
    api_version: "v1",
    supported_capabilities: ["IDENTITY_AUTH", "STUDENT_PROFILE_READ", "ENROLLMENTS_READ"],
    pilot_mode: "READ_ONLY_PILOT",
    feature_flags: {},
    timeouts_ms: { connect: 5000, read: 10000 },
    rate_limit_rpm: 600,
    active: true,
  }),
  getHealth: vi.fn().mockResolvedValue({
    status: "HEALTHY",
    connectivity: true,
    latency_ms: 38.5,
    details: { ready: true },
    checked_at: new Date().toISOString(),
  }),
  getReadiness: vi.fn().mockResolvedValue({
    university_id: "10000000-0000-0000-0000-000000000001",
    tenant_key: "zarqa",
    overall_status: "PASS",
    checklist: {
      TENANT_CONFIG_EXISTS: "PASS",
      INTEGRATION_CONFIG_EXISTS: "PASS",
      CONNECTIVITY_PROBE: "PASS",
      COURSE_MAPPINGS_COVERAGE: "PASS",
    },
    mapping_coverage: { course: 100, overall: 100 },
    summary_ar: "جميع المتطلبات الفنية للإطلاق التجريبي مكتملة ومطابقة للمعايير.",
    evaluated_at: new Date().toISOString(),
  }),
  listMappings: vi.fn().mockResolvedValue([
    {
      id: "map-1",
      university_id: "10000000-0000-0000-0000-000000000001",
      entity_type: "COURSE",
      external_code: "EXT-CS101",
      canonical_id: "0301101",
      canonical_code: "CAN-CS101",
    },
  ]),
  listSyncJobs: vi.fn().mockResolvedValue([
    {
      id: "job-1",
      university_id: "10000000-0000-0000-0000-000000000001",
      sync_mode: "FULL_SYNC",
      status: "SUCCEEDED",
      records_processed: 68,
      records_created: 68,
      records_updated: 0,
      records_skipped: 0,
      records_failed: 0,
      duration_ms: 450,
      started_at: new Date().toISOString(),
    },
  ]),
  listReconciliation: vi.fn().mockResolvedValue([
    {
      id: "rec-1",
      university_id: "10000000-0000-0000-0000-000000000001",
      entity_type: "STUDENT",
      external_identifier: "209900001",
      status: "IN_SYNC",
      details: {},
      detected_at: new Date().toISOString(),
    },
  ]),
  triggerSync: vi.fn(),
  saveMapping: vi.fn(),
  deleteMapping: vi.fn(),
}));

test("renders institutional integrations dashboard and navigates tabs", async () => {
  render(<IntegrationsDashboardPage />);

  // Heading check
  expect(screen.getByText("بوابة ربط الجامعات وأنظمة SIS")).toBeDefined();

  // Wait for tenant data to load
  await waitFor(() => {
    expect(screen.getByText("متصل وسليم")).toBeDefined();
  });

  // Check overview tab content
  expect(screen.getByText("بيانات المستأجر (Tenant Invariants)")).toBeDefined();
  expect(screen.getByText("zarqa")).toBeDefined();

  // Switch to Readiness tab
  const readinessBtn = screen.getByRole("button", { name: /بطاقة الجاهزية/ });
  fireEvent.click(readinessBtn);
  await waitFor(() => {
    expect(screen.getByText(/قائمة التدقيق الفني للإطلاق التجريبي/)).toBeDefined();
    expect(screen.getByText("TENANT_CONFIG_EXISTS")).toBeDefined();
  });

  // Switch to Mappings tab
  const mappingsBtn = screen.getByRole("button", { name: /مطابقة الخطط والمواد/ });
  fireEvent.click(mappingsBtn);
  await waitFor(() => {
    expect(screen.getByText("جدول المطابقة الأكاديمية (Curriculum Mappings)")).toBeDefined();
    expect(screen.getByText("EXT-CS101")).toBeDefined();
  });

  // Switch to Webhooks tab
  const webhooksBtn = screen.getByRole("button", { name: /أحداث الويب/ });
  fireEvent.click(webhooksBtn);
  await waitFor(() => {
    expect(screen.getByText("تكامل إشعارات الويب (Inbound Webhooks)")).toBeDefined();
    expect(screen.getByText(/X-Morshidi-Signature/)).toBeDefined();
  });
});
