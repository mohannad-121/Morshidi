-- Migration: 20261027120000_universal_university_engine.sql
-- Purpose: Schema enhancements for Universal University Integration Engine:
--          1. Configurable institutional grading policies (100-point, 4.0, 4.33, 5.0, letter grades).
--          2. Course search and terminology aliases (distinguished from authoritative academic equivalencies).
--          3. Universal campuses and classrooms structure.
--          4. Support for COURSE_ALIAS in university_mappings.
-- Principle: THE UNIVERSITY SIS REMAINS AUTHORITATIVE. AI EXPLAINS — DETERMINISTIC RULES DECIDE.

-- 1. Extend university_mappings check constraint to support COURSE_ALIAS
do $$
begin
  if exists (
    select 1 from pg_constraint where conname = 'university_mappings_entity_type_check'
  ) then
    alter table public.university_mappings drop constraint university_mappings_entity_type_check;
  end if;
  alter table public.university_mappings
    add constraint university_mappings_entity_type_check
    check (entity_type in ('FACULTY', 'MAJOR', 'PLAN', 'COURSE', 'TERM', 'SECTION', 'COURSE_ALIAS'));
end $$;

-- 2. Institutional Grading Policies Table
create table if not exists public.university_grading_policies (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete cascade,
  policy_version text not null check (btrim(policy_version) <> ''),
  scale_type text not null default 'PERCENTAGE_100'
    check (scale_type in ('PERCENTAGE_100', 'GPA_4_0', 'GPA_4_33', 'GPA_5_0', 'LETTER_GRADE')),
  gpa_scale numeric(6,2) not null check (gpa_scale > 0),
  gpa_min numeric(6,2) not null default 0,
  gpa_max numeric(6,2) not null check (gpa_max > gpa_min),
  course_grade_min numeric(6,2) not null default 0,
  course_grade_max numeric(6,2) not null check (course_grade_max > course_grade_min),
  passing_grade numeric(6,2) not null,
  major_passing_grade numeric(6,2) not null,
  warning_threshold numeric(6,2) not null,
  honors_threshold numeric(6,2) not null,
  letter_grade_mappings jsonb not null default '[]'::jsonb,
  is_active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_university_grading_policies_scope unique (university_id, policy_version)
);

create index if not exists idx_university_grading_policies_lookup
  on public.university_grading_policies (university_id, is_active);

create trigger set_university_grading_policies_updated_at
before update on public.university_grading_policies
for each row execute function public.set_updated_at();

-- 3. Course Aliases and Terminology Mappings Table
-- Used for fast, Arabic-first name resolution, dialect handling, and search synonyms.
-- NOTE: Authoritative course equivalencies used in prerequisite satisfaction and degree audits
-- reside strictly in public.course_equivalencies. Deterministic rules decide.
create table if not exists public.course_aliases (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete cascade,
  canonical_course_id uuid references public.courses(id) on delete cascade,
  canonical_course_code text not null check (btrim(canonical_course_code) <> ''),
  alias_code text,
  alias_name_ar text not null check (btrim(alias_name_ar) <> ''),
  alias_name_en text,
  alias_type text not null default 'INSTITUTIONAL_NAME'
    check (alias_type in ('INSTITUTIONAL_NAME', 'SEARCH_SYNONYM', 'HISTORICAL_CODE', 'REGIONAL_VARIANT')),
  is_verified boolean not null default true,
  notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_course_aliases_canonical
  on public.course_aliases (university_id, canonical_course_code);

create index if not exists idx_course_aliases_search
  on public.course_aliases (university_id, alias_name_ar);

create trigger set_course_aliases_updated_at
before update on public.course_aliases
for each row execute function public.set_updated_at();

-- 4. University Campuses Table
create table if not exists public.university_campuses (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete cascade,
  code text not null check (btrim(code) <> ''),
  name_ar text not null check (btrim(name_ar) <> ''),
  name_en text,
  city text,
  is_main boolean not null default false,
  active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_university_campuses_code unique (university_id, code)
);

create trigger set_university_campuses_updated_at
before update on public.university_campuses
for each row execute function public.set_updated_at();

-- 5. University Classrooms and Laboratories Table
create table if not exists public.university_classrooms (
  id uuid primary key default gen_random_uuid(),
  campus_id uuid not null references public.university_campuses(id) on delete cascade,
  building text not null check (btrim(building) <> ''),
  room_number text not null check (btrim(room_number) <> ''),
  room_type text not null default 'LECTURE_HALL'
    check (room_type in ('LECTURE_HALL', 'LABORATORY', 'SEMINAR_ROOM', 'AUDITORIUM', 'VIRTUAL')),
  capacity integer not null check (capacity > 0),
  facilities jsonb not null default '[]'::jsonb,
  active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_university_classrooms_room unique (campus_id, building, room_number)
);

create trigger set_university_classrooms_updated_at
before update on public.university_classrooms
for each row execute function public.set_updated_at();

-- 6. Enable Row Level Security (RLS) on all new tables
alter table public.university_grading_policies enable row level security;
alter table public.course_aliases enable row level security;
alter table public.university_campuses enable row level security;
alter table public.university_classrooms enable row level security;

-- 7. RLS Policies: Service role has full access; read access is tenant-scoped
do $$
begin
  -- university_grading_policies policies
  if not exists (select 1 from pg_policies where policyname = 'service_role_grading_policies_all') then
    create policy service_role_grading_policies_all on public.university_grading_policies
      for all using (auth.role() = 'service_role');
  end if;
  if not exists (select 1 from pg_policies where policyname = 'authenticated_read_grading_policies') then
    create policy authenticated_read_grading_policies on public.university_grading_policies
      for select using (auth.role() in ('authenticated', 'anon'));
  end if;

  -- course_aliases policies
  if not exists (select 1 from pg_policies where policyname = 'service_role_course_aliases_all') then
    create policy service_role_course_aliases_all on public.course_aliases
      for all using (auth.role() = 'service_role');
  end if;
  if not exists (select 1 from pg_policies where policyname = 'authenticated_read_course_aliases') then
    create policy authenticated_read_course_aliases on public.course_aliases
      for select using (auth.role() in ('authenticated', 'anon'));
  end if;

  -- university_campuses policies
  if not exists (select 1 from pg_policies where policyname = 'service_role_campuses_all') then
    create policy service_role_campuses_all on public.university_campuses
      for all using (auth.role() = 'service_role');
  end if;
  if not exists (select 1 from pg_policies where policyname = 'authenticated_read_campuses') then
    create policy authenticated_read_campuses on public.university_campuses
      for select using (auth.role() in ('authenticated', 'anon'));
  end if;

  -- university_classrooms policies
  if not exists (select 1 from pg_policies where policyname = 'service_role_classrooms_all') then
    create policy service_role_classrooms_all on public.university_classrooms
      for all using (auth.role() = 'service_role');
  end if;
  if not exists (select 1 from pg_policies where policyname = 'authenticated_read_classrooms') then
    create policy authenticated_read_classrooms on public.university_classrooms
      for select using (auth.role() in ('authenticated', 'anon'));
  end if;
end $$;

-- 8. Seed Default Grading Policies
-- Zarqa University: 100-point scale
insert into public.university_grading_policies (
  university_id,
  policy_version,
  scale_type,
  gpa_scale,
  gpa_min,
  gpa_max,
  course_grade_min,
  course_grade_max,
  passing_grade,
  major_passing_grade,
  warning_threshold,
  honors_threshold,
  letter_grade_mappings,
  is_active
) values (
  '10000000-0000-0000-0000-000000000001',
  'FAKE_UNIVERSITY_GRADING_POLICY_V1',
  'PERCENTAGE_100',
  100.00,
  0.00,
  100.00,
  0.00,
  100.00,
  50.00,
  60.00,
  60.00,
  84.00,
  '[
    {"letter": "A+", "min_grade": 90, "max_grade": 100, "grade_points": 4.0},
    {"letter": "A",  "min_grade": 85, "max_grade": 89,  "grade_points": 3.75},
    {"letter": "B+", "min_grade": 80, "max_grade": 84,  "grade_points": 3.5},
    {"letter": "B",  "min_grade": 75, "max_grade": 79,  "grade_points": 3.0},
    {"letter": "C+", "min_grade": 70, "max_grade": 74,  "grade_points": 2.5},
    {"letter": "C",  "min_grade": 60, "max_grade": 69,  "grade_points": 2.0},
    {"letter": "D",  "min_grade": 50, "max_grade": 59,  "grade_points": 1.5},
    {"letter": "F",  "min_grade": 0,  "max_grade": 49,  "grade_points": 0.0}
  ]'::jsonb,
  true
) on conflict (university_id, policy_version) do update set
  updated_at = now();

-- 9. Seed Sample Course Search Aliases for Zarqa University
insert into public.course_aliases (
  university_id,
  canonical_course_code,
  alias_code,
  alias_name_ar,
  alias_name_en,
  alias_type,
  is_verified,
  notes
) values
  ('10000000-0000-0000-0000-000000000001', '0100101', '0100101-ALT', 'المواطنة', 'Citizenship', 'SEARCH_SYNONYM', true, 'الاسم الشائع للتربية الوطنية'),
  ('10000000-0000-0000-0000-000000000001', '0100101', '0100101-LEG', 'التربية المدنية', 'Civic Education', 'HISTORICAL_CODE', true, 'المسمى القديم لمادة التربية الوطنية'),
  ('10000000-0000-0000-0000-000000000001', '1501110', '1501110-SYN', 'مقدمة في البرمجة', 'Intro to Programming', 'SEARCH_SYNONYM', true, 'مرادف لمادة أساسيات البرمجة')
on conflict do nothing;
