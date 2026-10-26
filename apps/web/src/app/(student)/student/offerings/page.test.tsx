import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import OfferingsPage, { normalizeCourseSearch } from "./page";

const api = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api/use-authenticated-api", () => ({ useAuthenticatedApi: () => api }));

const identities = [
  { course_id: "c1", course_code: "CS101", name_ar: "مُقَدِّمة البرمجة", name_en: "Programming Introduction" },
  { course_id: "c2", course_code: "MATH101", name_ar: "رياضيات متقطعة", name_en: "Discrete Mathematics" },
];
const section = { section_id: "SYN-CS101-A", course_code: "CS101", status: "OPEN",
  modality: "IN_PERSON", campus: "FICTIONAL-CAMPUS", location: "SYNTHETIC-ROOM",
  meetings: [{ day: 1, starts_at: "09:00", ends_at: "11:00", timezone: "Asia/Amman" }],
  capacity: 30, enrolled: 10, available: null, waitlist: null,
  capacity_state: "KNOWN_OPEN", provenance: "SYNTHETIC_SANDBOX_FACT" };
const catalog = { operational_state: "AVAILABLE", source_type: "SYNTHETIC",
  source_version: "p10-synthetic-v1", fresh_until: "2027-09-01", coverage_complete: true,
  provenance: "SANDBOX / SYNTHETIC DATA", sections: [section] };
const course = { course_code: "CS101", academic_decision: "ELIGIBLE", operational_state: "SECTION_OPEN",
  source_type: "SYNTHETIC", source_version: "p10-synthetic-v1", fresh_until: "2027-09-01",
  coverage_complete: true, provenance: "SANDBOX / SYNTHETIC DATA", sections: [section] };
const periods = { status: "AVAILABLE", periods: [
  { period_key: "2025-SPRING", name_ar: "الفصل الماضي", name_en: "Past semester", starts_on: "2025-02-01",
    ends_on: "2025-06-01", source_type: "SYNTHETIC", provenance: "SYNTHETIC", registration_open: false },
  { period_key: "2026-FALL", name_ar: "الفصل الحالي", name_en: "Current semester", starts_on: "2026-09-01",
    ends_on: "2026-12-31", source_type: "SYNTHETIC", provenance: "SYNTHETIC", registration_open: true },
  { period_key: "2027-SPRING", name_ar: "الفصل القادم", name_en: "Future semester", starts_on: "2027-02-01",
    ends_on: "2027-06-01", source_type: "SYNTHETIC", provenance: "SYNTHETIC", registration_open: false },
] };

beforeEach(() => {
  api.request.mockReset();
  api.request.mockImplementation((path: string) => {
    if (path === "/api/v1/me/course-identities") return Promise.resolve(new Response(JSON.stringify(identities)));
    if (path === "/api/v1/me/offerings/periods") return Promise.resolve(new Response(JSON.stringify(periods)));
    if (path.startsWith("/api/v1/me/offerings?")) return Promise.resolve(new Response(JSON.stringify(catalog)));
    if (path.includes("/api/v1/me/offerings/CS101")) return Promise.resolve(new Response(JSON.stringify(course)));
    return Promise.resolve(new Response("{}"));
  });
});

test("normalizes Arabic diacritics, tatweel, alef variants, and alif maqsura", () => {
  expect(normalizeCourseSearch("إِدَارَةُ الـمُحتوى")).toBe("ادارة المحتوي");
});

test("loads the registration-open semester and its initial course list without manual entry", async () => {
  render(<OfferingsPage />);
  expect(document.querySelector("main[dir='rtl']")).toBeTruthy();
  expect(await screen.findByRole("option", { name: /الفصل الحالي.*التسجيل مفتوح/ })).toBeDefined();
  await screen.findByText("مُقَدِّمة البرمجة");
  expect((screen.getByLabelText("العام الأكاديمي") as HTMLSelectElement).value).toBe("2026");
  expect((screen.getByLabelText("الفصل الدراسي") as HTMLSelectElement).value).toBe("2026-FALL");
  expect(api.request.mock.calls.some((call: unknown[]) => String(call[0]).includes("period_key=2026-FALL"))).toBe(true);
});

test("Arabic first-character search and keyboard selection use the canonical course identity", async () => {
  render(<OfferingsPage />);
  const input = await screen.findByRole("combobox", { name: "ابحث عن مادة" });
  fireEvent.change(input, { target: { value: "مق" } });
  expect(await screen.findByRole("option", { name: /مُقَدِّمة البرمجة/ })).toBeDefined();
  fireEvent.keyDown(input, { key: "ArrowDown" });
  fireEvent.keyDown(input, { key: "Enter" });
  await screen.findByText(/مؤهل أكاديمياً/);
  expect(api.request.mock.calls.some((call: unknown[]) => String(call[0]).includes("/offerings/CS101?"))).toBe(true);
});

test("English-name and course-code matching work after switching direction", async () => {
  render(<OfferingsPage />);
  fireEvent.click(screen.getByRole("button", { name: "Switch language" }));
  expect(document.querySelector("main[dir='ltr']")).toBeTruthy();
  const input = await screen.findByRole("combobox", { name: "Search courses" });
  fireEvent.change(input, { target: { value: "program" } });
  expect(await screen.findByRole("option", { name: /Programming Introduction/ })).toBeDefined();
  fireEvent.change(input, { target: { value: "CS101" } });
  expect(await screen.findByRole("option", { name: /CS101/ })).toBeDefined();
});

test("past and future academic-year selections reload their tenant-scoped periods", async () => {
  render(<OfferingsPage />);
  await screen.findByRole("option", { name: /الفصل الحالي/ });
  fireEvent.change(screen.getByLabelText("العام الأكاديمي"), { target: { value: "2025" } });
  await waitFor(() => expect((screen.getByLabelText("الفصل الدراسي") as HTMLSelectElement).value).toBe("2025-SPRING"));
  fireEvent.change(screen.getByLabelText("العام الأكاديمي"), { target: { value: "2027" } });
  await waitFor(() => expect((screen.getByLabelText("الفصل الدراسي") as HTMLSelectElement).value).toBe("2027-SPRING"));
});

test("uses the exact Arabic search and verified-empty messages", async () => {
  api.request.mockImplementation((path: string) => {
    if (path === "/api/v1/me/course-identities") return Promise.resolve(new Response(JSON.stringify(identities)));
    if (path === "/api/v1/me/offerings/periods") return Promise.resolve(new Response(JSON.stringify(periods)));
    return Promise.resolve(new Response(JSON.stringify({ ...catalog, operational_state: "NO_OFFERINGS", sections: [] })));
  });
  render(<OfferingsPage />);
  expect(await screen.findByText("لا يوجد مواد لهذا الفصل")).toBeDefined();
  fireEvent.change(screen.getByRole("combobox", { name: "ابحث عن مادة" }), { target: { value: "غير موجود" } });
  expect(await screen.findByText("لا توجد مواد مطابقة لبحثك")).toBeDefined();
});

test.each([
  ["OFFERING_COVERAGE_INCOMPLETE", "بيانات هذا الفصل غير مكتملة"],
  ["PROVIDER_UNAVAILABLE", "مزود العروض غير متاح"],
  ["SNAPSHOT_STALE", "بيانات العروض قديمة"],
])("renders %s as a distinct non-empty state", async (operationalState, expected) => {
  api.request.mockImplementation((path: string) => {
    if (path === "/api/v1/me/course-identities") return Promise.resolve(new Response(JSON.stringify(identities)));
    if (path === "/api/v1/me/offerings/periods") return Promise.resolve(new Response(JSON.stringify(periods)));
    return Promise.resolve(new Response(JSON.stringify({ ...catalog, operational_state: operationalState,
      sections: operationalState === "SNAPSHOT_STALE" ? [section] : [] })));
  });
  render(<OfferingsPage />);
  expect((await screen.findByText(new RegExp(expected))).textContent).toContain(expected);
  expect(screen.queryByText("لا يوجد مواد لهذا الفصل")).toBeNull();
});

test("explicit planner overlay preserves academic rank and displays typed conflicts", async () => {
  const planner = { academic_planner: { plan_options: [{ rank: 1, courses: [] }] },
    offering_overlay: [{ academic_rank: 1, course_codes: ["CS101", "MATH101"], selected_section_ids: null,
      operational_status: "NO_CONFIRMED_SET_OR_INCOMPLETE_DATA", possible_pair_conflicts: [{ reason: "TIME_OVERLAP",
        first_section_id: "SYN-CS101-A", second_section_id: "SYN-MATH101-A", day: 1,
        starts_at: "10:00", ends_at: "11:00", timezone: "Asia/Amman" }] }],
    source_type: "SYNTHETIC", source_version: "v1", provenance: "SYNTHETIC", fresh_until: "2027-09-01",
    planning_scope: "ACADEMIC_RESULT_PLUS_EXPLICIT_OPERATIONAL_OVERLAY" };
  api.request.mockImplementation((path: string) => {
    if (path === "/api/v1/me/course-identities") return Promise.resolve(new Response(JSON.stringify(identities)));
    if (path === "/api/v1/me/offerings/periods") return Promise.resolve(new Response(JSON.stringify(periods)));
    if (path.includes("semester-plans/offerings")) return Promise.resolve(new Response(JSON.stringify(planner)));
    return Promise.resolve(new Response(JSON.stringify(catalog)));
  });
  render(<OfferingsPage />);
  await screen.findByRole("option", { name: /الفصل الحالي/ });
  fireEvent.click(screen.getByRole("button", { name: "مقارنة الخطة الأكاديمية بالعروض" }));
  const conflict = await screen.findByText(/تعارض في أوقات المحاضرات/);
  expect(conflict.closest("div")?.textContent).toContain("SYN-MATH101-A");
  expect(conflict.closest("div")?.textContent).toContain("الاثنين");
  expect(conflict.closest("div")?.textContent).toContain("10:00 ص – 11:00 ص");
});

test("course-name search matches partial Arabic words, fills full name on selection, and shows status badge", async () => {
  render(<OfferingsPage />);
  const input = (await screen.findByRole("combobox", { name: "ابحث عن مادة" })) as HTMLInputElement;

  // Search by partial word in the middle: "برمجة" matches "مُقَدِّمة البرمجة"
  fireEvent.change(input, { target: { value: "برمجة" } });
  const option = await screen.findByRole("option", { name: /مُقَدِّمة البرمجة/ });
  expect(option).toBeDefined();

  // Verify badge indicating offered status
  expect(option.textContent).toContain("مطروحة هذا الفصل");

  // Click suggestion
  fireEvent.click(option);

  // Input should now contain the full course name
  expect(input.value).toBe("مُقَدِّمة البرمجة");

  // Eligibility and sections should load for the canonical code CS101 with elegant Arabic labels
  await screen.findByText(/مؤهل أكاديمياً/);
  expect(api.request.mock.calls.some((call: unknown[]) => String(call[0]).includes("/offerings/CS101?"))).toBe(true);
});

test("Teh-Marbuta variation matches in autocomplete", async () => {
  render(<OfferingsPage />);
  const input = await screen.findByRole("combobox", { name: "ابحث عن مادة" });

  // Type "مقدمه" with Heh instead of Teh Marbuta
  fireEvent.change(input, { target: { value: "مقدمه" } });
  expect(await screen.findByRole("option", { name: /مُقَدِّمة البرمجة/ })).toBeDefined();
});

test("clear search button resets query and selection, and Escape closes dropdown", async () => {
  render(<OfferingsPage />);
  const input = (await screen.findByRole("combobox", { name: "ابحث عن مادة" })) as HTMLInputElement;

  fireEvent.change(input, { target: { value: "رياضيات" } });
  expect(await screen.findByRole("option", { name: /رياضيات متقطعة/ })).toBeDefined();

  // Escape dismisses dropdown
  fireEvent.keyDown(input, { key: "Escape" });
  await waitFor(() => {
    expect(screen.queryByRole("option", { name: /رياضيات متقطعة/ })).toBeNull();
  });

  // Re-open on focus or down arrow
  fireEvent.focus(input);
  expect(await screen.findByRole("option", { name: /رياضيات متقطعة/ })).toBeDefined();

  // Clear button resets search
  const clearBtn = screen.getByRole("button", { name: "مسح البحث" });
  fireEvent.click(clearBtn);
  expect(input.value).toBe("");
  expect(screen.queryByRole("option", { name: /رياضيات متقطعة/ })).toBeNull();
});

test("renders polished Arabic section cards and suppresses raw technical metadata", async () => {
  render(<OfferingsPage />);
  const input = await screen.findByRole("combobox", { name: "ابحث عن مادة" });
  fireEvent.change(input, { target: { value: "برمجة" } });
  const option = await screen.findByRole("option", { name: /مُقَدِّمة البرمجة/ });
  fireEvent.click(option);

  // Status badges in Arabic
  await screen.findByText("مؤهل أكاديمياً");
  expect(screen.getByText("الشعبة مفتوحة")).toBeDefined();

  // Section card details in elegant Arabic
  expect(screen.getByText("وجاهي")).toBeDefined();
  expect(screen.getByText("مقاعد متاحة")).toBeDefined();
  expect(screen.getByText("الاثنين")).toBeDefined();
  expect(screen.getByText(/09:00 ص – 11:00 ص/)).toBeDefined();
  expect(screen.getByText(/10 \/ 30/)).toBeDefined();

  // Raw machine internals must NEVER be displayed
  expect(screen.queryByText(/\bELIGIBLE\b/)).toBeNull();
  expect(screen.queryByText(/\bKNOWN_OPEN\b/)).toBeNull();
  expect(screen.queryByText(/\bIN_PERSON\b/)).toBeNull();
  expect(screen.queryByText(/\bAsia\/Amman\b/)).toBeNull();
  expect(screen.queryByText(/\bp10-synthetic-v1\b/)).toBeNull();
});
