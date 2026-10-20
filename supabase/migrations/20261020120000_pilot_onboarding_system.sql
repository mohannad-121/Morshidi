-- Migration: 20261020120000_pilot_onboarding_system.sql
-- Purpose: Schema foundation for first university pilot package, onboarding workflow,
--          requirements tracking, blocker management, acceptance gates, and sign-offs.
-- Principles: AI EXPLAINS — DETERMINISTIC RULES DECIDE. THE UNIVERSITY SIS REMAINS AUTHORITATIVE.
--             READ-ONLY FIRST. ZERO SECRETS IN METADATA.

-- 1. University Pilots (Engagement Model)
create table if not exists public.university_pilots (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete cascade,
  pilot_name text not null check (btrim(pilot_name) <> ''),
  status text not null default 'DRAFT'
    check (status in (
      'DRAFT',
      'DISCOVERY',
      'WAITING_FOR_UNIVERSITY_IT',
      'TECHNICAL_REQUIREMENTS_RECEIVED',
      'SANDBOX_PREPARATION',
      'IDENTITY_CONFIGURATION',
      'ACADEMIC_MAPPING',
      'SECURITY_REVIEW',
      'TECHNICAL_VALIDATION',
      'READ_ONLY_PILOT_READY',
      'READ_ONLY_PILOT_ACTIVE',
      'READ_ONLY_PILOT_ACCEPTANCE',
      'WRITE_PILOT_REVIEW',
      'WRITE_ENABLED_PILOT_READY',
      'GO_LIVE_REVIEW',
      'ACCEPTED',
      'BLOCKED',
      'SUSPENDED',
      'CANCELLED'
    )),
  mode text not null default 'READ_ONLY_PILOT'
    check (mode in ('READ_ONLY_PILOT', 'WRITE_ENABLED_PILOT')),
  target_start_date date,
  target_end_date date,
  cohort_scope jsonb not null default '{}'::jsonb,
  discovery_intake jsonb not null default '{}'::jsonb,
  technical_questionnaire jsonb not null default '{}'::jsonb,
  security_questionnaire jsonb not null default '{}'::jsonb,
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_university_pilots_uni_name unique (university_id, pilot_name)
);

create index if not exists idx_university_pilots_university_status
  on public.university_pilots (university_id, status);

create trigger set_university_pilots_updated_at
before update on public.university_pilots
for each row execute function public.set_updated_at();

-- 2. Pilot Stakeholders (Operational Contact Roles)
create table if not exists public.university_pilot_stakeholders (
  id uuid primary key default gen_random_uuid(),
  pilot_id uuid not null references public.university_pilots(id) on delete cascade,
  role text not null
    check (role in (
      'MORSHIDI_PLATFORM_ADMIN',
      'UNIVERSITY_TECHNICAL_CONTACT',
      'UNIVERSITY_ACADEMIC_CONTACT',
      'UNIVERSITY_PILOT_SPONSOR',
      'UNIVERSITY_SECURITY_CONTACT',
      'REGISTRAR_CONTACT',
      'NETWORK_CONTACT',
      'IDENTITY_CONTACT'
    )),
  name text not null check (btrim(name) <> ''),
  title text not null default '',
  email text not null check (btrim(email) <> ''),
  phone text not null default '',
  notes text not null default '',
  created_at timestamptz not null default now()
);

create index if not exists idx_university_pilot_stakeholders_pilot
  on public.university_pilot_stakeholders (pilot_id);

-- 3. University IT Requirements Checklist
create table if not exists public.university_pilot_requirements (
  id uuid primary key default gen_random_uuid(),
  pilot_id uuid not null references public.university_pilots(id) on delete cascade,
  requirement_key text not null check (btrim(requirement_key) <> ''),
  category text not null
    check (category in (
      'SIS_API',
      'IDENTITY_SSO',
      'ACADEMIC_DATA',
      'SECURITY',
      'SANDBOX',
      'NETWORK',
      'LEGAL_OPERATIONAL'
    )),
  title_ar text not null check (btrim(title_ar) <> ''),
  title_en text not null check (btrim(title_en) <> ''),
  importance text not null default 'REQUIRED'
    check (importance in ('REQUIRED', 'OPTIONAL', 'NOT_APPLICABLE')),
  status text not null default 'NOT_REQUESTED'
    check (status in (
      'NOT_REQUESTED',
      'REQUESTED',
      'RECEIVED',
      'VALIDATED',
      'REJECTED',
      'NOT_APPLICABLE'
    )),
  secret_ref_name text,
  notes text not null default '',
  validated_at timestamptz,
  validated_by text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_university_pilot_requirements_key unique (pilot_id, requirement_key)
);

create index if not exists idx_university_pilot_requirements_pilot
  on public.university_pilot_requirements (pilot_id, category);

create trigger set_university_pilot_requirements_updated_at
before update on public.university_pilot_requirements
for each row execute function public.set_updated_at();

-- 4. Pilot Blockers
create table if not exists public.university_pilot_blockers (
  id uuid primary key default gen_random_uuid(),
  pilot_id uuid not null references public.university_pilots(id) on delete cascade,
  blocker_code text not null check (btrim(blocker_code) <> ''),
  title_ar text not null check (btrim(title_ar) <> ''),
  severity text not null default 'SEV2'
    check (severity in ('SEV1', 'SEV2', 'SEV3', 'SEV4')),
  owner_role text not null default 'UNIVERSITY_TECHNICAL_CONTACT',
  status text not null default 'OPEN'
    check (status in ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'WONT_FIX')),
  resolution_notes text not null default '',
  resolved_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_university_pilot_blockers_pilot
  on public.university_pilot_blockers (pilot_id, status);

create trigger set_university_pilot_blockers_updated_at
before update on public.university_pilot_blockers
for each row execute function public.set_updated_at();

-- 5. Pilot Acceptance Checks
create table if not exists public.university_pilot_acceptance_checks (
  id uuid primary key default gen_random_uuid(),
  pilot_id uuid not null references public.university_pilots(id) on delete cascade,
  check_key text not null check (btrim(check_key) <> ''),
  category text not null
    check (category in (
      'IDENTITY',
      'ACADEMIC_DATA',
      'MAPPING',
      'STUDENT_EXPERIENCE',
      'INSTITUTIONAL_EXPERIENCE',
      'SECURITY',
      'OPERATIONS'
    )),
  title_ar text not null check (btrim(title_ar) <> ''),
  title_en text not null check (btrim(title_en) <> ''),
  importance text not null default 'REQUIRED'
    check (importance in ('REQUIRED', 'OPTIONAL')),
  is_automated boolean not null default false,
  status text not null default 'NOT_TESTED'
    check (status in ('PASS', 'FAIL', 'WARNING', 'NOT_APPLICABLE', 'NOT_TESTED')),
  evidence_ref text not null default '',
  tested_by text not null default '',
  tested_at timestamptz,
  notes text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_university_pilot_acceptance_key unique (pilot_id, check_key)
);

create index if not exists idx_university_pilot_acceptance_pilot
  on public.university_pilot_acceptance_checks (pilot_id, category);

create trigger set_university_pilot_acceptance_updated_at
before update on public.university_pilot_acceptance_checks
for each row execute function public.set_updated_at();

-- 6. Pilot Operational Sign-Offs
create table if not exists public.university_pilot_signoffs (
  id uuid primary key default gen_random_uuid(),
  pilot_id uuid not null references public.university_pilots(id) on delete cascade,
  signoff_role text not null
    check (signoff_role in (
      'TECHNICAL_SIGN_OFF',
      'ACADEMIC_VALIDATION_SIGN_OFF',
      'PILOT_SPONSOR_FINAL_SIGN_OFF',
      'MORSHIDI_PLATFORM_SIGN_OFF'
    )),
  signee_name text not null check (btrim(signee_name) <> ''),
  signee_role text not null check (btrim(signee_role) <> ''),
  status text not null default 'PENDING'
    check (status in ('PENDING', 'APPROVED', 'REJECTED')),
  decision_notes text not null default '',
  signed_at timestamptz,
  created_at timestamptz not null default now(),
  constraint uq_university_pilot_signoffs_role unique (pilot_id, signoff_role)
);

create index if not exists idx_university_pilot_signoffs_pilot
  on public.university_pilot_signoffs (pilot_id);

-- 7. Pilot Activity Audit Trail
create table if not exists public.university_pilot_activity (
  id uuid primary key default gen_random_uuid(),
  pilot_id uuid not null references public.university_pilots(id) on delete cascade,
  action text not null check (btrim(action) <> ''),
  actor_id uuid,
  actor_email text not null default '',
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_university_pilot_activity_pilot
  on public.university_pilot_activity (pilot_id, created_at desc);

-- 8. Row Level Security & Multi-Tenant Authorization
alter table public.university_pilots enable row level security;
alter table public.university_pilot_stakeholders enable row level security;
alter table public.university_pilot_requirements enable row level security;
alter table public.university_pilot_blockers enable row level security;
alter table public.university_pilot_acceptance_checks enable row level security;
alter table public.university_pilot_signoffs enable row level security;
alter table public.university_pilot_activity enable row level security;

-- Revoke anon and public access
revoke all on public.university_pilots from anon, public;
revoke all on public.university_pilot_stakeholders from anon, public;
revoke all on public.university_pilot_requirements from anon, public;
revoke all on public.university_pilot_blockers from anon, public;
revoke all on public.university_pilot_acceptance_checks from anon, public;
revoke all on public.university_pilot_signoffs from anon, public;
revoke all on public.university_pilot_activity from anon, public;

-- Grant service role full access
grant all on public.university_pilots to service_role;
grant all on public.university_pilot_stakeholders to service_role;
grant all on public.university_pilot_requirements to service_role;
grant all on public.university_pilot_blockers to service_role;
grant all on public.university_pilot_acceptance_checks to service_role;
grant all on public.university_pilot_signoffs to service_role;
grant all on public.university_pilot_activity to service_role;

-- Grant authenticated users read access strictly through institutional membership
grant select on public.university_pilots to authenticated;
grant select on public.university_pilot_stakeholders to authenticated;
grant select on public.university_pilot_requirements to authenticated;
grant select on public.university_pilot_blockers to authenticated;
grant select on public.university_pilot_acceptance_checks to authenticated;
grant select on public.university_pilot_signoffs to authenticated;
grant select on public.university_pilot_activity to authenticated;

-- Policies: university_pilots
create policy university_pilots_admin_read on public.university_pilots
  for select to authenticated
  using (
    exists (
      select 1 from public.institutional_memberships m
      where m.subject_user_id = (select auth.uid())
        and m.university_id = university_pilots.university_id
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );

-- Policies: university_pilot_stakeholders
create policy university_pilot_stakeholders_admin_read on public.university_pilot_stakeholders
  for select to authenticated
  using (
    exists (
      select 1 from public.university_pilots p
      join public.institutional_memberships m on m.university_id = p.university_id
      where p.id = university_pilot_stakeholders.pilot_id
        and m.subject_user_id = (select auth.uid())
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );

-- Policies: university_pilot_requirements
create policy university_pilot_requirements_admin_read on public.university_pilot_requirements
  for select to authenticated
  using (
    exists (
      select 1 from public.university_pilots p
      join public.institutional_memberships m on m.university_id = p.university_id
      where p.id = university_pilot_requirements.pilot_id
        and m.subject_user_id = (select auth.uid())
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );

-- Policies: university_pilot_blockers
create policy university_pilot_blockers_admin_read on public.university_pilot_blockers
  for select to authenticated
  using (
    exists (
      select 1 from public.university_pilots p
      join public.institutional_memberships m on m.university_id = p.university_id
      where p.id = university_pilot_blockers.pilot_id
        and m.subject_user_id = (select auth.uid())
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );

-- Policies: university_pilot_acceptance_checks
create policy university_pilot_acceptance_checks_admin_read on public.university_pilot_acceptance_checks
  for select to authenticated
  using (
    exists (
      select 1 from public.university_pilots p
      join public.institutional_memberships m on m.university_id = p.university_id
      where p.id = university_pilot_acceptance_checks.pilot_id
        and m.subject_user_id = (select auth.uid())
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );

-- Policies: university_pilot_signoffs
create policy university_pilot_signoffs_admin_read on public.university_pilot_signoffs
  for select to authenticated
  using (
    exists (
      select 1 from public.university_pilots p
      join public.institutional_memberships m on m.university_id = p.university_id
      where p.id = university_pilot_signoffs.pilot_id
        and m.subject_user_id = (select auth.uid())
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );

-- Policies: university_pilot_activity
create policy university_pilot_activity_admin_read on public.university_pilot_activity
  for select to authenticated
  using (
    exists (
      select 1 from public.university_pilots p
      join public.institutional_memberships m on m.university_id = p.university_id
      where p.id = university_pilot_activity.pilot_id
        and m.subject_user_id = (select auth.uid())
        and m.role in ('INSTITUTIONAL_ANALYST', 'ACADEMIC_ADVISOR')
        and m.active = true
    )
  );
