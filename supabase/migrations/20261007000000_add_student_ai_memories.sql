-- Migration: Add student AI personalization memories for Morshidi
-- Personalization memory ONLY: stores user-stated academic preferences and goals.
-- Academic facts (GPA, credits, grades, prerequisites, eligibility) MUST NEVER be stored here.

create table if not exists public.student_ai_memories (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  institution_id uuid not null references public.universities(id) on delete restrict,
  memory_category text not null check (memory_category in ('ACADEMIC_INTEREST', 'WORKLOAD_PREFERENCE', 'CAREER_GOAL', 'SCHEDULE_CONSTRAINT')),
  memory_key text not null check (length(memory_key) between 1 and 64),
  memory_value text not null check (length(memory_value) between 1 and 255),
  provenance text not null default 'USER_STATED' check (provenance = 'USER_STATED'),
  source_thread_id uuid references public.student_conversation_threads(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_user_id, institution_id, memory_key)
);

create index if not exists student_ai_memories_owner_idx on public.student_ai_memories
  (owner_user_id, institution_id, memory_category);

create or replace function public.validate_student_ai_memory_scope()
returns trigger language plpgsql set search_path = '' as $$
begin
  -- 1. Verify owner owns an existing student_academic_profile at the stated institution
  if not exists (
    select 1 from public.student_academic_profiles p
    join public.study_plans sp on sp.id = p.study_plan_id
    join public.majors m on m.id = sp.major_id
    join public.faculties f on f.id = m.faculty_id
    where p.owner_user_id = new.owner_user_id and f.university_id = new.institution_id
  ) then
    raise exception 'Student AI memory owner/institution scope mismatch' using errcode = '23514';
  end if;

  -- 2. If source_thread_id is set, verify referenced thread matches id, owner_user_id, and institution_id
  if new.source_thread_id is not null and not exists (
    select 1 from public.student_conversation_threads t
    where t.id = new.source_thread_id
      and t.owner_user_id = new.owner_user_id
      and t.institution_id = new.institution_id
  ) then
    raise exception 'Student AI memory source thread scope mismatch' using errcode = '23514';
  end if;

  return new;
end;
$$;

drop trigger if exists student_ai_memory_scope_guard on public.student_ai_memories;
create trigger student_ai_memory_scope_guard
before insert or update on public.student_ai_memories
for each row execute function public.validate_student_ai_memory_scope();

alter table public.student_ai_memories enable row level security;

revoke all on public.student_ai_memories from anon, authenticated;
grant select on public.student_ai_memories to authenticated;
grant select, insert, update, delete on public.student_ai_memories to service_role;

drop policy if exists student_ai_memories_owner_select on public.student_ai_memories;
create policy student_ai_memories_owner_select on public.student_ai_memories
  for select to authenticated
  using (
    owner_user_id = auth.uid() and exists (
      select 1 from public.student_academic_profiles p
      join public.study_plans sp on sp.id = p.study_plan_id
      join public.majors m on m.id = sp.major_id
      join public.faculties f on f.id = m.faculty_id
      where p.owner_user_id = auth.uid() and f.university_id = student_ai_memories.institution_id
    )
  );

revoke all on function public.validate_student_ai_memory_scope() from public, anon, authenticated;
grant execute on function public.validate_student_ai_memory_scope() to service_role;
