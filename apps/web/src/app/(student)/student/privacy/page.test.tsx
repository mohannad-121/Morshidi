import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
import PrivacyPage from "./page";

const client = vi.hoisted(() => ({ request: vi.fn() }));
vi.mock("@/lib/api/use-authenticated-api", () => ({ useAuthenticatedApi: () => client }));

const summary = { status: "LOCAL_MODEL_ONLY", purposes: ["ACADEMIC_SUPPORT", "PRODUCT_EVALUATION"],
  consents: [], participation: [], requests: [], feedback: [], retention: [],
  study_label: "SYNTHETIC STUDY — NO REAL PARTICIPANTS", limitations: ["NO_PRODUCTION_PERSISTENCE"] };
const studies = { studies: [{ study_id: "study-1", title_ar: "دراسة اصطناعية", title_en: "Synthetic study",
  version: "v1", consent_version: "v1", label: "SYNTHETIC STUDY — NO REAL PARTICIPANTS", tasks: [] }] };

beforeEach(() => {
  client.request.mockReset();
  client.request.mockImplementation((path: string) => Promise.resolve(new Response(JSON.stringify(
    path === "/api/v1/me/privacy/studies" ? studies : summary))));
});

test("Arabic RTL and English LTR privacy controls disclose synthetic limits", async () => {
  render(<PrivacyPage />);
  expect(screen.getByRole("status").textContent).toContain("التحميل");
  await screen.findByText(/نموذج محلي فقط/);
  expect(document.querySelector("main[dir='rtl']")).toBeTruthy();
  expect(screen.getByRole("button", { name: "الموافقة على دراسة اصطناعية" })).toBeTruthy();
  expect(screen.getByText(/لا توجد سياسة احتفاظ معتمدة/)).toBeTruthy();
  await userEvent.click(screen.getByRole("button", { name: "Switch language" }));
  expect(document.querySelector("main[dir='ltr']")).toBeTruthy();
  expect(screen.getByText(/no real participants or approved retention policy/i)).toBeTruthy();
});

test("consent action uses owner-scoped API without student ID", async () => {
  render(<PrivacyPage />);
  await screen.findByText(/نموذج محلي فقط/);
  await userEvent.click(screen.getByRole("button", { name: "الموافقة على دراسة اصطناعية" }));
  expect(client.request).toHaveBeenCalledWith("/api/v1/me/privacy/consents", expect.objectContaining({
    method: "POST", body: expect.stringContaining('"study_id":"study-1"'),
  }));
  const call = client.request.mock.calls.find(([path]) => path === "/api/v1/me/privacy/consents");
  expect(call?.[1]?.body).not.toContain("student_id");
});

test("provider failure remains an unavailable state with no false success", async () => {
  client.request.mockRejectedValue(new Error("offline"));
  render(<PrivacyPage />);
  await screen.findByRole("alert");
  expect(screen.getByText(/لم تُغيَّر بياناتك/)).toBeTruthy();
});

test("granted consent is visible and withdrawal uses its owner-scoped ID", async () => {
  const granted = { ...summary, consents: [{ consent_id: "consent-own", purpose: "PRODUCT_EVALUATION",
    consent_version: "v1", policy_reference: "SYNTHETIC_STUDY:study-1:v1",
    scopes: ["study:study-1"], status: "GRANTED", granted_at: "2026-10-01T00:00:00Z", withdrawn_at: null }] };
  client.request.mockImplementation((path: string) => Promise.resolve(new Response(JSON.stringify(
    path === "/api/v1/me/privacy/studies" ? studies : granted))));
  render(<PrivacyPage />);
  await screen.findByText(/PRODUCT_EVALUATION · GRANTED/);
  await userEvent.click(screen.getByRole("button", { name: "سحب الموافقة" }));
  expect(client.request).toHaveBeenCalledWith("/api/v1/me/privacy/consents/consent-own/withdraw",
    expect.objectContaining({ method: "POST" }));
});

test("correction and deletion controls submit bounded owner-only requests", async () => {
  render(<PrivacyPage />);
  await screen.findByText(/نموذج محلي فقط/);
  await screen.findByRole("button", { name: /إرسال الطلب للمراجعة · طلب تصحيح/ });
  await userEvent.type(screen.getByRole("textbox", { name: "سبب الطلب" }), "Review this record");
  await userEvent.click(screen.getByRole("button", { name: /إرسال الطلب للمراجعة · طلب تصحيح/ }));
  expect(client.request).toHaveBeenCalledWith("/api/v1/me/privacy/requests", expect.objectContaining({
    body: expect.stringContaining('"kind":"CORRECTION"'),
  }));
  await userEvent.type(screen.getByRole("textbox", { name: "سبب الطلب" }), "Remove optional data");
  await userEvent.click(screen.getByRole("button", { name: /إرسال الطلب للمراجعة · طلب حذف/ }));
  expect(client.request).toHaveBeenCalledWith("/api/v1/me/privacy/requests", expect.objectContaining({
    body: expect.stringContaining('"kind":"DELETION"'),
  }));
});

test("keyboard language control is reachable", async () => {
  render(<PrivacyPage />);
  await userEvent.tab();
  expect(document.activeElement).toBe(screen.getByRole("button", { name: "Switch language" }));
  await userEvent.keyboard("{Enter}");
  expect(document.querySelector("main[dir='ltr']")).toBeTruthy();
});
