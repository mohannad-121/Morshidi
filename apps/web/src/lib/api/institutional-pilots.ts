import type { AuthenticatedApiClient } from "./authenticated-client";

export type PilotStatus =
  | "DRAFT"
  | "DISCOVERY"
  | "WAITING_FOR_UNIVERSITY_IT"
  | "TECHNICAL_REQUIREMENTS_RECEIVED"
  | "SANDBOX_PREPARATION"
  | "IDENTITY_CONFIGURATION"
  | "ACADEMIC_MAPPING"
  | "SECURITY_REVIEW"
  | "TECHNICAL_VALIDATION"
  | "READ_ONLY_PILOT_READY"
  | "READ_ONLY_PILOT_ACTIVE"
  | "READ_ONLY_PILOT_ACCEPTANCE"
  | "WRITE_PILOT_REVIEW"
  | "WRITE_ENABLED_PILOT_READY"
  | "GO_LIVE_REVIEW"
  | "ACCEPTED"
  | "BLOCKED"
  | "SUSPENDED"
  | "CANCELLED";

export type PilotMode = "READ_ONLY_PILOT" | "WRITE_ENABLED_PILOT";

export type PilotCohortScope = {
  faculties: string[];
  majors: string[];
  academic_plans: string[];
  target_terms: string[];
  estimated_student_count: number;
  scope_notes: string;
};

export type DiscoveryIntake = {
  university_name_official: string;
  country: string;
  timezone: string;
  preferred_locale: string;
  sis_vendor: string;
  hosting_model: string;
  api_available: boolean;
  api_version: string;
  sandbox_available: boolean;
  documentation_available: boolean;
  identity_protocol: string;
  academic_structure_summary: string;
  network_restrictions: string;
  notes: string;
};

export type UniversityPilot = {
  id: string;
  university_id: string;
  pilot_name: string;
  status: PilotStatus;
  mode: PilotMode;
  target_start_date?: string | null;
  target_end_date?: string | null;
  cohort_scope: PilotCohortScope;
  discovery_intake: DiscoveryIntake;
  technical_questionnaire: Record<string, unknown>;
  security_questionnaire: Record<string, unknown>;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type PilotSummary = {
  pilot_id: string;
  pilot_name: string;
  status: PilotStatus;
  mode: PilotMode;
  current_phase: string;
  technical_readiness_score: string;
  operational_readiness_score: string;
  mapping_coverage_pct: number;
  open_critical_blockers_count: number;
  open_total_blockers_count: number;
  requirements_validated_count: number;
  requirements_total_count: number;
  acceptance_passed_count: number;
  acceptance_total_count: number;
  last_sync_status?: string | null;
  target_start_date?: string | null;
  target_end_date?: string | null;
};

export type PilotRequirement = {
  id: string;
  pilot_id: string;
  requirement_key: string;
  category: "SIS_API" | "IDENTITY_SSO" | "ACADEMIC_DATA" | "SECURITY" | "SANDBOX" | "NETWORK" | "LEGAL_OPERATIONAL";
  title_ar: string;
  title_en: string;
  importance: "REQUIRED" | "OPTIONAL" | "NOT_APPLICABLE";
  status: "NOT_REQUESTED" | "REQUESTED" | "RECEIVED" | "VALIDATED" | "REJECTED" | "NOT_APPLICABLE";
  secret_ref_name?: string | null;
  notes: string;
  validated_at?: string | null;
  validated_by?: string | null;
  created_at: string;
};

export type PilotBlocker = {
  id: string;
  pilot_id: string;
  blocker_code: string;
  title_ar: string;
  severity: "SEV1" | "SEV2" | "SEV3" | "SEV4";
  owner_role: string;
  status: "OPEN" | "IN_PROGRESS" | "RESOLVED" | "WONT_FIX";
  resolution_notes: string;
  resolved_at?: string | null;
  created_at: string;
};

export type PilotStakeholder = {
  id: string;
  pilot_id: string;
  role: string;
  name: string;
  title: string;
  email: string;
  phone: string;
  notes: string;
  created_at: string;
};

export type PilotAcceptanceCheck = {
  id: string;
  pilot_id: string;
  check_key: string;
  category: "IDENTITY" | "ACADEMIC_DATA" | "MAPPING" | "STUDENT_EXPERIENCE" | "INSTITUTIONAL_EXPERIENCE" | "SECURITY" | "OPERATIONS";
  title_ar: string;
  title_en: string;
  importance: "REQUIRED" | "OPTIONAL";
  is_automated: boolean;
  status: "PASS" | "FAIL" | "WARNING" | "NOT_APPLICABLE" | "NOT_TESTED";
  evidence_ref: string;
  tested_by: string;
  tested_at?: string | null;
  notes: string;
};

export type PilotSignoff = {
  id: string;
  pilot_id: string;
  signoff_role: "TECHNICAL_SIGN_OFF" | "ACADEMIC_VALIDATION_SIGN_OFF" | "PILOT_SPONSOR_FINAL_SIGN_OFF" | "MORSHIDI_PLATFORM_SIGN_OFF";
  signee_name: string;
  signee_role: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  decision_notes: string;
  signed_at?: string | null;
  created_at: string;
};

export type WriteEnablementCheck = {
  check_key: string;
  title_ar: string;
  title_en: string;
  status: "PASS" | "FAIL" | "WARNING";
  details: string;
};

export type WriteEnablementResult = {
  pilot_id: string;
  overall_status: "PASS" | "FAIL";
  can_enable_write: boolean;
  checks: WriteEnablementCheck[];
  summary_ar: string;
};

export type PilotReport = {
  pilot_id: string;
  university_id: string;
  university_name: string;
  pilot_name: string;
  mode: PilotMode;
  status: PilotStatus;
  technical_readiness: Record<string, unknown>;
  mapping_coverage: Record<string, number>;
  sync_health: Record<string, unknown>;
  security_status: Record<string, unknown>;
  acceptance_results: Record<string, unknown>;
  open_blockers: PilotBlocker[];
  signoffs: PilotSignoff[];
  final_recommendation: "ACCEPTED" | "ACCEPTED_WITH_WARNINGS" | "BLOCKED";
  generated_at: string;
};

export type PilotActivity = {
  id: string;
  pilot_id: string;
  action: string;
  actor_id?: string | null;
  actor_email: string;
  details: Record<string, unknown>;
  created_at: string;
};

// ---------------------------------------------------------------------------
// Client API Functions
// ---------------------------------------------------------------------------

async function fetchJson<T>(
  client: AuthenticatedApiClient,
  path: `/api/v1/institutional/pilots${string}`,
  init?: RequestInit,
): Promise<T> {
  const response = await client.request(path, init);
  if (!response.ok) {
    throw new Error(`API_ERROR_${response.status}`);
  }
  return (await response.json()) as T;
}

async function requestVoid(
  client: AuthenticatedApiClient,
  path: `/api/v1/institutional/pilots${string}`,
  init?: RequestInit,
): Promise<void> {
  const response = await client.request(path, init);
  if (!response.ok) {
    throw new Error(`API_ERROR_${response.status}`);
  }
}

export async function listPilots(api: AuthenticatedApiClient, universityId?: string): Promise<UniversityPilot[]> {
  const query = universityId ? `?university_id=${encodeURIComponent(universityId)}` : "";
  return fetchJson<UniversityPilot[]>(api, `/api/v1/institutional/pilots${query}`);
}

export async function getPilot(api: AuthenticatedApiClient, pilotId: string): Promise<UniversityPilot> {
  return fetchJson<UniversityPilot>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}`);
}

export async function createPilot(api: AuthenticatedApiClient, payload: Partial<UniversityPilot>): Promise<UniversityPilot> {
  return fetchJson<UniversityPilot>(api, "/api/v1/institutional/pilots", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updatePilot(api: AuthenticatedApiClient, pilotId: string, payload: Partial<UniversityPilot>): Promise<UniversityPilot> {
  return fetchJson<UniversityPilot>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function transitionPilot(api: AuthenticatedApiClient, pilotId: string, targetStatus: PilotStatus, notes = ""): Promise<UniversityPilot> {
  return fetchJson<UniversityPilot>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/transition`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ target_status: targetStatus, notes }),
  });
}

export async function getPilotSummary(api: AuthenticatedApiClient, pilotId: string): Promise<PilotSummary> {
  return fetchJson<PilotSummary>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/summary`);
}

export async function listPilotRequirements(api: AuthenticatedApiClient, pilotId: string): Promise<PilotRequirement[]> {
  return fetchJson<PilotRequirement[]>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/requirements`);
}

export async function updatePilotRequirement(
  api: AuthenticatedApiClient,
  pilotId: string,
  requirementKey: string,
  payload: { status: string; secret_ref_name?: string | null; notes?: string; validated_by?: string | null }
): Promise<PilotRequirement> {
  return fetchJson<PilotRequirement>(
    api,
    `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/requirements/${encodeURIComponent(requirementKey)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function listPilotBlockers(api: AuthenticatedApiClient, pilotId: string): Promise<PilotBlocker[]> {
  return fetchJson<PilotBlocker[]>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/blockers`);
}

export async function createPilotBlocker(
  api: AuthenticatedApiClient,
  pilotId: string,
  payload: { blocker_code: string; title_ar: string; severity: string; owner_role: string; resolution_notes?: string }
): Promise<PilotBlocker> {
  return fetchJson<PilotBlocker>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/blockers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function updatePilotBlocker(
  api: AuthenticatedApiClient,
  pilotId: string,
  blockerId: string,
  payload: { status: string; resolution_notes: string }
): Promise<PilotBlocker> {
  return fetchJson<PilotBlocker>(
    api,
    `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/blockers/${encodeURIComponent(blockerId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function listPilotStakeholders(api: AuthenticatedApiClient, pilotId: string): Promise<PilotStakeholder[]> {
  return fetchJson<PilotStakeholder[]>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/stakeholders`);
}

export async function addPilotStakeholder(
  api: AuthenticatedApiClient,
  pilotId: string,
  payload: { role: string; name: string; email: string; title?: string; phone?: string; notes?: string }
): Promise<PilotStakeholder> {
  return fetchJson<PilotStakeholder>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/stakeholders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function deletePilotStakeholder(api: AuthenticatedApiClient, pilotId: string, stakeholderId: string): Promise<void> {
  return requestVoid(
    api,
    `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/stakeholders/${encodeURIComponent(stakeholderId)}`,
    { method: "DELETE" }
  );
}

export async function listPilotAcceptanceChecks(api: AuthenticatedApiClient, pilotId: string): Promise<PilotAcceptanceCheck[]> {
  return fetchJson<PilotAcceptanceCheck[]>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/acceptance`);
}

export async function runAutomatedAcceptance(api: AuthenticatedApiClient, pilotId: string): Promise<PilotAcceptanceCheck[]> {
  return fetchJson<PilotAcceptanceCheck[]>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/acceptance/run`, {
    method: "POST",
  });
}

export async function updatePilotAcceptanceCheck(
  api: AuthenticatedApiClient,
  pilotId: string,
  checkKey: string,
  payload: { status: string; evidence_ref?: string; notes?: string }
): Promise<PilotAcceptanceCheck> {
  return fetchJson<PilotAcceptanceCheck>(
    api,
    `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/acceptance/${encodeURIComponent(checkKey)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function listPilotSignoffs(api: AuthenticatedApiClient, pilotId: string): Promise<PilotSignoff[]> {
  return fetchJson<PilotSignoff[]>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/signoffs`);
}

export async function recordPilotSignoff(
  api: AuthenticatedApiClient,
  pilotId: string,
  payload: { signoff_role: string; signee_name: string; signee_role: string; status: string; decision_notes?: string }
): Promise<PilotSignoff> {
  return fetchJson<PilotSignoff>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/signoffs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function getPilotWriteEnablement(api: AuthenticatedApiClient, pilotId: string): Promise<WriteEnablementResult> {
  return fetchJson<WriteEnablementResult>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/write-enablement`);
}

export async function getPilotReport(api: AuthenticatedApiClient, pilotId: string): Promise<PilotReport> {
  return fetchJson<PilotReport>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/report`);
}

export async function listPilotActivity(api: AuthenticatedApiClient, pilotId: string): Promise<PilotActivity[]> {
  return fetchJson<PilotActivity[]>(api, `/api/v1/institutional/pilots/${encodeURIComponent(pilotId)}/activity`);
}
