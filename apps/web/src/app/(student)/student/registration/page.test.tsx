import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RegistrationPage from "./page";

const request = vi.fn();
const client = { request };
vi.mock("@/lib/api/use-authenticated-api", () => ({ useAuthenticatedApi: () => client }));

const section = { id: "SEC-CS101-1", courseCode: "CS101", courseName: "مقدمة في البرمجة", sectionNumber: 1,
  credits: 3, instructor: "د. تجريبي", days: "ح ث خ", daysArray: ["الأحد"], startTime: "09:00", endTime: "10:00",
  room: "IT-101", capacity: 30, enrolled: 10, status: "متاحة", availableSeats: 20, requirementGroup: "متطلب تخصص",
  prerequisites: [], eligibility: { state: "ELIGIBLE", label: "مؤهل" } };

function response(body: unknown) { return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } }); }

describe("official registration page", () => {
  beforeEach(() => {
    request.mockReset();
    request.mockImplementation((path: string) => {
      if (path.endsWith("/context")) return Promise.resolve(response({ success: true, context: {
        term: { code: "2026-1", label: "الفصل الأول" }, registrationOpen: true,
        registrationWindow: { start: null, end: null }, currentEnrollments: [], registeredCredits: 0,
        policy: { kind: "FAKE_UNIVERSITY_DEMO_POLICY", maxCreditHours: 18 }, planKey: "ZU:IT:CS:P12",
      } }));
      if (path.endsWith("/offerings")) return Promise.resolve(response({ success: true, offerings: [section] }));
      if (path.endsWith("/preview")) return Promise.resolve(response({ success: true, preview: {
        canRegister: true, selectedSections: [section], resultingSections: [section], resultingCredits: 3, maxCredits: 18, issues: [],
      } }));
      if (path.endsWith("/register")) return Promise.resolve(response({ success: true, duplicate: false, enrollments: [section] }));
      throw new Error(`unexpected ${path}`);
    });
  });

  it("loads plan-safe offerings, requires preview, and confirms authoritative registration", async () => {
    render(<RegistrationPage />);
    expect(await screen.findByText("مقدمة في البرمجة")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "إضافة للسلة" }));
    fireEvent.click(screen.getByRole("button", { name: "معاينة رسمية" }));
    expect(await screen.findByText("المعاينة صالحة للتأكيد")).toBeDefined();
    fireEvent.click(screen.getByRole("button", { name: "تأكيد التسجيل لدى الجامعة" }));
    await waitFor(() => expect(screen.getByText("أكدت الجامعة الافتراضية التسجيل وتم تحديث جدولك.")).toBeDefined());
    expect(request.mock.calls.some(([path, init]) => path.endsWith("/register") && init.headers["Idempotency-Key"])).toBe(true);
  });
});
