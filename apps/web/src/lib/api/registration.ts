import { AuthenticatedApiClient } from "@/lib/api/authenticated-client";

export type RegistrationCode = "ELIGIBLE" | "NOT_ELIGIBLE" | "REVIEW_REQUIRED" |
  "ALREADY_REGISTERED" | "SECTION_FULL" | "SCHEDULE_CONFLICT" |
  "CREDIT_LIMIT_EXCEEDED" | "REGISTRATION_CLOSED" | "COURSE_NOT_OFFERED" | "INVALID_SECTION";

export interface RegistrationSection {
  id: string; courseCode: string; courseName: string; sectionNumber: number; credits: number;
  instructor: string; days: string; daysArray: string[]; startTime: string; endTime: string;
  meetings?: Array<{ day: string; startTime: string; endTime: string }>;
  room: string; capacity: number; enrolled: number; status: string; availableSeats?: number;
  requirementGroup?: string; prerequisites?: string[];
  eligibility?: { state: "ELIGIBLE" | "NOT_ELIGIBLE" | "REVIEW_REQUIRED"; label: string; reason?: string };
}

export interface RegistrationContext {
  term: { code: string; label: string }; registrationOpen: boolean;
  registrationWindow: { start: string | null; end: string | null };
  currentEnrollments: RegistrationSection[]; registeredCredits: number;
  policy: { kind: "FAKE_UNIVERSITY_DEMO_POLICY"; maxCreditHours: number }; planKey: string;
}

export interface RegistrationIssue {
  code: RegistrationCode; sectionId?: string; courseCode?: string; relatedSectionId?: string;
  messageAr: string; messageEn: string;
}

export interface RegistrationPreview {
  canRegister: boolean; selectedSections: RegistrationSection[]; resultingSections: RegistrationSection[];
  resultingCredits: number; maxCredits: number; issues: RegistrationIssue[];
}

async function json<T>(response: Response): Promise<T> {
  if (!response.ok) throw new Error(`HTTP_${response.status}`);
  return response.json() as Promise<T>;
}

export class RegistrationApi {
  constructor(private readonly client: AuthenticatedApiClient) {}
  async context() { return (await json<{ success: boolean; context: RegistrationContext }>(
    await this.client.request("/api/v1/me/registration/context", { cache: "no-store" }))).context; }
  async offerings() { return (await json<{ success: boolean; offerings: RegistrationSection[] }>(
    await this.client.request("/api/v1/me/registration/offerings", { cache: "no-store" }))).offerings; }
  async preview(sectionIds: string[]) { return (await json<{ preview: RegistrationPreview }>(
    await this.client.request("/api/v1/me/registration/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ section_ids: sectionIds }) }))).preview; }
  async register(sectionIds: string[], key: string) { return json<{ success: boolean; duplicate: boolean; enrollments: RegistrationSection[] }>(
    await this.client.request("/api/v1/me/registration/register", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": key }, body: JSON.stringify({ section_ids: sectionIds }) })); }
  async drop(sectionId: string, key: string) { return json<{ success: boolean; duplicate: boolean; enrollments: RegistrationSection[] }>(
    await this.client.request("/api/v1/me/registration/drop", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": key }, body: JSON.stringify({ section_id: sectionId }) })); }
}
