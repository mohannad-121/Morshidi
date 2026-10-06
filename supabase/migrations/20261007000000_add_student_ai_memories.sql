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

alter table public.student_ai_memories enable row level security;

revoke all on public.student_ai_memories from anon, authenticated;
grant select on public.student_ai_memories to authenticated;

drop policy if exists student_ai_memories_owner_select on public.student_ai_memories;
create policy student_ai_memories_owner_select on public.student_ai_memories
  for select to authenticated
  using (owner_user_id = auth.uid());

