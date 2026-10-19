-- Migration: 20261020100000_sis_integration_readiness.sql
-- Purpose: Schema foundation for generic university tenant onboarding, SIS adapter architecture,
--          capability negotiation, curriculum/identity mapping, sync tracking, and reconciliation.
-- Principle: THE UNIVERSITY SIS REMAINS AUTHORITATIVE. AI EXPLAINS — DETERMINISTIC RULES DECIDE.

-- 1. Extend public.universities with tenant key, status, and locale configuration
alter table public.universities
  add column if not exists tenant_key text,
  add column if not exists timezone text not null default 'Asia/Amman',
  add column if not exists default_locale text not null default 'ar',
  add column if not exists status text not null default 'ACTIVE'
    check (status in ('DRAFT', 'CONFIGURING', 'VALIDATING', 'PILOT_READY', 'ACTIVE', 'SUSPENDED'));

-- Backfill tenant_key for default Zarqa University and any existing rows
update public.universities
set tenant_key = case
  when id = '10000000-0000-0000-0000-000000000001' then 'zarqa'
  else lower(coalesce(nullif(regexp_replace(country, '[^a-zA-Z0-9]', '', 'g'), ''), 'tenant')) || '-' || replace(id::text, '-', '')
end
where tenant_key is null;

-- Make tenant_key unique and not null
alter table public.universities
  alter column tenant_key set not null;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'uq_universities_tenant_key'
  ) then
    alter table public.universities
      add constraint uq_universities_tenant_key unique (tenant_key);
  end if;
end $$;

-- 2. University Integration Configuration (Credentials referenced safely via env keys, never plaintext secrets)
create table if not exists public.university_integration_configs (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete cascade,
  provider_type text not null check (btrim(provider_type) <> ''),
  base_url text not null check (btrim(base_url) <> ''),
  auth_method text not null default 'client_credentials'
    check (auth_method in ('client_credentials', 'token', 'basic', 'sso')),
  client_id text,
  secret_env_ref text,
  token_url text,
  api_version text not null default 'v1',
  supported_capabilities jsonb not null default '[]'::jsonb,
  pilot_mode text not null default 'READ_ONLY_PILOT'
    check (pilot_mode in ('READ_ONLY_PILOT', 'WRITE_ENABLED_PILOT')),
  feature_flags jsonb not null default '{}'::jsonb,
  timeouts_ms jsonb not null default '{"connect": 5000, "read": 10000}'::jsonb,
  rate_limit_rpm integer not null default 600,
  webhook_secret_env_ref text,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_university_integration_configs_uni_provider unique (university_id, provider_type)
);

create trigger set_university_integration_configs_updated_at
before update on public.university_integration_configs
for each row execute function public.set_updated_at();

-- 3. External-to-Canonical Curriculum & Entity Mappings
create table if not exists public.university_mappings (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete cascade,
  entity_type text not null
    check (entity_type in ('FACULTY', 'MAJOR', 'PLAN', 'COURSE', 'TERM', 'SECTION')),
  external_code text not null check (btrim(external_code) <> ''),
  canonical_id text not null check (btrim(canonical_id) <> ''),
  canonical_code text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_university_mappings_scope unique (university_id, entity_type, external_code)
);

create index if not exists idx_university_mappings_lookup
  on public.university_mappings (university_id, entity_type);

create trigger set_university_mappings_updated_at
before update on public.university_mappings
for each row execute function public.set_updated_at();

-- 4. Synchronization Job Ledger (Full Sync, Incremental Sync, Event-Driven)
create table if not exists public.university_sync_jobs (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete cascade,
  sync_mode text not null
    check (sync_mode in ('FULL_SYNC', 'INCREMENTAL_SYNC', 'EVENT_DRIVEN')),
  status text not null default 'PENDING'
    check (status in ('PENDING', 'RUNNING', 'SUCCEEDED', 'PARTIAL', 'FAILED')),
  cursor_before text,
  cursor_after text,
  records_processed integer not null default 0,
  records_created integer not null default 0,
  records_updated integer not null default 0,
  records_skipped integer not null default 0,
  records_failed integer not null default 0,
  warnings jsonb not null default '[]'::jsonb,
  errors jsonb not null default '[]'::jsonb,
  duration_ms integer not null default 0,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_university_sync_jobs_tenant_started
  on public.university_sync_jobs (university_id, started_at desc);

-- 5. Reconciliation Drift Ledger
create table if not exists public.university_reconciliation_items (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete cascade,
  entity_type text not null
    check (entity_type in ('STUDENT', 'ENROLLMENT', 'GRADE', 'PLAN', 'COURSE')),
  external_identifier text not null check (btrim(external_identifier) <> ''),
  status text not null
    check (status in ('IN_SYNC', 'MISSING_LOCALLY', 'STALE_LOCALLY', 'VALUE_MISMATCH', 'IDENTITY_MISMATCH', 'MAPPING_MISSING')),
  details jsonb not null default '{}'::jsonb,
  detected_at timestamptz not null default now(),
  resolved_at timestamptz
);

create index if not exists idx_university_reconciliation_tenant_status
  on public.university_reconciliation_items (university_id, status);

-- 6. Integration Audit Log
create table if not exists public.university_integration_audit_log (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete cascade,
  action text not null check (btrim(action) <> ''),
  actor_user_id uuid,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_university_integration_audit_tenant_time
  on public.university_integration_audit_log (university_id, created_at desc);

-- 7. Additive extensions to student_university_identities for external SSO & profile linkage
alter table public.student_university_identities
  add column if not exists external_subject text,
  add column if not exists morshidi_profile_id uuid references public.student_academic_profiles(id) on delete set null,
  add column if not exists idp_issuer text,
  add column if not exists link_status text not null default 'LINKED'
    check (link_status in ('LINKED', 'PENDING', 'CONFLICT', 'UNLINKED'));

-- 8. Row Level Security & Privilege Grants
alter table public.university_integration_configs enable row level security;
alter table public.university_mappings enable row level security;
alter table public.university_sync_jobs enable row level security;
alter table public.university_reconciliation_items enable row level security;
alter table public.university_integration_audit_log enable row level security;

revoke all on table public.university_integration_configs from anon, authenticated;
revoke all on table public.university_mappings from anon, authenticated;
revoke all on table public.university_sync_jobs from anon, authenticated;
revoke all on table public.university_reconciliation_items from anon, authenticated;
revoke all on table public.university_integration_audit_log from anon, authenticated;

grant select, insert, update, delete on table public.university_integration_configs to service_role;
grant select, insert, update, delete on table public.university_mappings to service_role;
grant select, insert, update, delete on table public.university_sync_jobs to service_role;
grant select, insert, update, delete on table public.university_reconciliation_items to service_role;
grant select, insert, update, delete on table public.university_integration_audit_log to service_role;

-- Allow authenticated institutional administrators/analysts to inspect integration state for their authorized university only
grant select on table public.university_integration_configs to authenticated;
grant select on table public.university_mappings to authenticated;
grant select on table public.university_sync_jobs to authenticated;
grant select on table public.university_reconciliation_items to authenticated;
grant select on table public.university_integration_audit_log to authenticated;

create policy university_integration_configs_admin_read on public.university_integration_configs
  for select to authenticated
  using (
    exists (
      select 1 from public.institutional_memberships m
      where m.subject_user_id = (select auth.uid())
        and m.university_id = university_integration_configs.university_id
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );

create policy university_mappings_admin_read on public.university_mappings
  for select to authenticated
  using (
    exists (
      select 1 from public.institutional_memberships m
      where m.subject_user_id = (select auth.uid())
        and m.university_id = university_mappings.university_id
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );

create policy university_sync_jobs_admin_read on public.university_sync_jobs
  for select to authenticated
  using (
    exists (
      select 1 from public.institutional_memberships m
      where m.subject_user_id = (select auth.uid())
        and m.university_id = university_sync_jobs.university_id
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );

create policy university_reconciliation_admin_read on public.university_reconciliation_items
  for select to authenticated
  using (
    exists (
      select 1 from public.institutional_memberships m
      where m.subject_user_id = (select auth.uid())
        and m.university_id = university_reconciliation_items.university_id
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );

create policy university_audit_admin_read on public.university_integration_audit_log
  for select to authenticated
  using (
    exists (
      select 1 from public.institutional_memberships m
      where m.subject_user_id = (select auth.uid())
        and m.university_id = university_integration_audit_log.university_id
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );
