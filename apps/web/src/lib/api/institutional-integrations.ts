import type { AuthenticatedApiClient } from "./authenticated-client";

export type UniversityTenant = {
  id: string;
  tenant_key: string;
  name_ar: string;
  name_en: string | null;
  country: string;
  timezone: string;
  default_locale: string;
  status: "DRAFT" | "CONFIGURING" | "VALIDATING" | "PILOT_READY" | "ACTIVE" | "SUSPENDED";
  active: boolean;
};

export type UniversityIntegrationConfig = {
  id?: string;
  university_id: string;
  provider_type: string;
  base_url: string;
  auth_method: "client_credentials" | "token" | "basic" | "sso";
  client_id?: string | null;
  secret_env_ref?: string | null;
  token_url?: string | null;
  api_version: string;
  supported_capabilities: string[];
  pilot_mode: "READ_ONLY_PILOT" | "WRITE_ENABLED_PILOT";
  feature_flags: Record<string, boolean>;
  timeouts_ms: { connect: number; read: number };
  rate_limit_rpm: number;
  webhook_secret_env_ref?: string | null;
  active: boolean;
};

export type HealthResult = {
  status: "HEALTHY" | "DEGRADED" | "UNHEALTHY" | "NOT_CONFIGURED";
  connectivity: boolean;
  latency_ms: number;
  details: Record<string, unknown>;
  checked_at: string;
};

export type PilotReadinessScorecard = {
  university_id: string;
  tenant_key: string;
  overall_status: "PASS" | "WARNING" | "FAIL";
  checklist: Record<string, "PASS" | "WARNING" | "FAIL" | "NOT_APPLICABLE">;
  mapping_coverage: Record<string, number>;
  summary_ar: string;
  evaluated_at: string;
};

export type UniversityMapping = {
  id?: string;
  university_id: string;
  entity_type: "FACULTY" | "MAJOR" | "PLAN" | "COURSE" | "TERM" | "SECTION";
  external_code: string;
  canonical_id: string;
  canonical_code?: string | null;
  metadata?: Record<string, unknown>;
};

export type SyncJob = {
  id: string;
  university_id: string;
  sync_mode: "FULL_SYNC" | "INCREMENTAL_SYNC" | "EVENT_DRIVEN";
  status: "PENDING" | "RUNNING" | "SUCCEEDED" | "PARTIAL" | "FAILED";
  cursor_before: string | null;
  cursor_after: string | null;
  records_processed: number;
  records_created: number;
  records_updated: number;
  records_skipped: number;
  records_failed: number;
  warnings: string[];
  errors: string[];
  duration_ms: number;
  started_at: string;
  completed_at: string | null;
};

export type ReconciliationItem = {
  id: string;
  university_id: string;
  entity_type: "STUDENT" | "ENROLLMENT" | "GRADE" | "PLAN" | "COURSE";
  external_identifier: string;
  status: "IN_SYNC" | "MISSING_LOCALLY" | "STALE_LOCALLY" | "VALUE_MISMATCH" | "IDENTITY_MISMATCH" | "MAPPING_MISSING";
  details: Record<string, unknown>;
  detected_at: string;
  resolved_at: string | null;
};

async function fetchJson<T>(
  client: AuthenticatedApiClient,
  path: `/api/v1/institutional/integrations${string}`,
  init?: RequestInit,
): Promise<T> {
  const response = await client.request(path, init);
  if (!response.ok) {
    throw new Error(`API_ERROR_${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function listTenants(client: AuthenticatedApiClient): Promise<UniversityTenant[]> {
  return fetchJson<UniversityTenant[]>(client, "/api/v1/institutional/integrations/tenants");
}

export async function getTenant(client: AuthenticatedApiClient, universityId: string): Promise<UniversityTenant> {
  return fetchJson<UniversityTenant>(client, `/api/v1/institutional/integrations/tenants/${universityId}`);
}

export async function getConfig(client: AuthenticatedApiClient, universityId: string): Promise<UniversityIntegrationConfig | null> {
  const response = await client.request(`/api/v1/institutional/integrations/config?university_id=${universityId}`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`API_ERROR_${response.status}`);
  return response.json() as Promise<UniversityIntegrationConfig>;
}

export async function saveConfig(client: AuthenticatedApiClient, config: UniversityIntegrationConfig): Promise<UniversityIntegrationConfig> {
  return fetchJson<UniversityIntegrationConfig>(client, "/api/v1/institutional/integrations/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
}

export async function getHealth(client: AuthenticatedApiClient, universityId: string): Promise<HealthResult> {
  return fetchJson<HealthResult>(client, `/api/v1/institutional/integrations/health?university_id=${universityId}`);
}

export async function getReadiness(client: AuthenticatedApiClient, universityId: string): Promise<PilotReadinessScorecard> {
  return fetchJson<PilotReadinessScorecard>(client, `/api/v1/institutional/integrations/readiness?university_id=${universityId}`);
}

export async function listMappings(
  client: AuthenticatedApiClient,
  universityId: string,
  entityType?: string,
): Promise<UniversityMapping[]> {
  const query = entityType ? `&entity_type=${entityType}` : "";
  return fetchJson<UniversityMapping[]>(client, `/api/v1/institutional/integrations/mappings?university_id=${universityId}${query}`);
}

export async function saveMapping(client: AuthenticatedApiClient, mapping: UniversityMapping): Promise<UniversityMapping> {
  return fetchJson<UniversityMapping>(client, "/api/v1/institutional/integrations/mappings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(mapping),
  });
}

export async function deleteMapping(client: AuthenticatedApiClient, universityId: string, mappingId: string): Promise<{ deleted: boolean }> {
  return fetchJson<{ deleted: boolean }>(client, `/api/v1/institutional/integrations/mappings/${mappingId}?university_id=${universityId}`, {
    method: "DELETE",
  });
}

export async function triggerSync(
  client: AuthenticatedApiClient,
  universityId: string,
  mode: "FULL_SYNC" | "INCREMENTAL_SYNC" = "FULL_SYNC",
  cursor?: string,
): Promise<SyncJob> {
  return fetchJson<SyncJob>(client, "/api/v1/institutional/integrations/sync", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ university_id: universityId, mode, cursor }),
  });
}

export async function listSyncJobs(client: AuthenticatedApiClient, universityId: string): Promise<SyncJob[]> {
  return fetchJson<SyncJob[]>(client, `/api/v1/institutional/integrations/sync/jobs?university_id=${universityId}`);
}

export async function listReconciliation(
  client: AuthenticatedApiClient,
  universityId: string,
  status?: string,
): Promise<ReconciliationItem[]> {
  const query = status ? `&status=${status}` : "";
  return fetchJson<ReconciliationItem[]>(client, `/api/v1/institutional/integrations/reconciliation?university_id=${universityId}${query}`);
}


