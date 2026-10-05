-- Migration: 20261005160000_create_student_university_identities.sql
-- Purpose: Durable mapping between Morshidi internal users (auth.users) and external university student identities.
-- Note: The external university remains the Source of Truth for university authentication and student ID.

create table public.student_university_identities (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  university_id uuid not null references public.universities(id) on delete restrict,
  university_student_id text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_synced_at timestamptz,
  constraint uq_student_university_identities_uni_student unique (university_id, university_student_id),
  constraint uq_student_university_identities_owner_uni unique (owner_user_id, university_id),
  constraint ck_student_university_identities_student_id check (length(btrim(university_student_id)) > 0)
);

comment on table public.student_university_identities is
  'Maps an authenticated Morshidi user (auth.users) to an external university student identity. External university is the Source of Truth.';

create index idx_student_university_identities_university
  on public.student_university_identities (university_id);

create trigger set_student_university_identities_updated_at
before update on public.student_university_identities
for each row execute function public.set_updated_at();

alter table public.student_university_identities enable row level security;

revoke all on table public.student_university_identities from anon, authenticated;

grant select on table public.student_university_identities to authenticated;
grant select, insert, update, delete on table public.student_university_identities to service_role;

create policy student_university_identities_owner_read
on public.student_university_identities
for select to authenticated
using ((select auth.uid()) = owner_user_id);
