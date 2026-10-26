-- Versioned deterministic graduation-policy model. Draft only: do not apply to production here.

begin;

create table public.graduation_policy_packages (
  id uuid primary key default gen_random_uuid(),
  university_id uuid not null references public.universities(id) on delete restrict,
  policy_code text not null check (btrim(policy_code) <> ''),
  name_ar text not null check (btrim(name_ar) <> ''),
  name_en text check (name_en is null or btrim(name_en) <> ''),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (university_id, policy_code),
  unique (id, university_id)
);

create table public.graduation_policy_versions (
  id uuid primary key default gen_random_uuid(),
  policy_package_id uuid not null references public.graduation_policy_packages(id) on delete restrict,
  version text not null check (btrim(version) <> ''),
  lifecycle_status text not null default 'draft'
    check (lifecycle_status in ('draft', 'validated', 'approved', 'retired')),
  effective_from date not null,
  effective_to date check (effective_to is null or effective_to >= effective_from),
  source_id uuid references public.academic_sources(id) on delete restrict,
  content_hash text not null check (btrim(content_hash) <> ''),
  validated_at timestamptz,
  validated_by uuid,
  approved_at timestamptz,
  approved_by uuid,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (policy_package_id, version),
  unique (id, policy_package_id),
  check (
    (lifecycle_status = 'draft')
    or (validated_at is not null and validated_by is not null)
  ),
  check (
    lifecycle_status not in ('approved', 'retired')
    or (approved_at is not null and approved_by is not null)
  )
);

create table public.graduation_policy_applicability (
  id uuid primary key default gen_random_uuid(),
  policy_version_id uuid not null references public.graduation_policy_versions(id) on delete restrict,
  university_id uuid not null references public.universities(id) on delete restrict,
  scope_level text not null check (scope_level in (
    'university', 'degree_level', 'faculty', 'program', 'study_plan'
  )),
  degree_level text check (degree_level is null or btrim(degree_level) <> ''),
  faculty_id uuid references public.faculties(id) on delete restrict,
  major_id uuid references public.majors(id) on delete restrict,
  study_plan_id uuid references public.study_plans(id) on delete restrict,
  created_at timestamptz not null default now(),
  unique (policy_version_id, scope_level, university_id, degree_level, faculty_id, major_id, study_plan_id),
  check (
    (scope_level = 'university' and degree_level is null and faculty_id is null and major_id is null and study_plan_id is null)
    or (scope_level = 'degree_level' and degree_level is not null and faculty_id is null and major_id is null and study_plan_id is null)
    or (scope_level = 'faculty' and faculty_id is not null and major_id is null and study_plan_id is null)
    or (scope_level = 'program' and major_id is not null and study_plan_id is null)
    or (scope_level = 'study_plan' and study_plan_id is not null)
  )
);

create table public.graduation_policy_rules (
  id uuid primary key default gen_random_uuid(),
  policy_version_id uuid not null references public.graduation_policy_versions(id) on delete restrict,
  rule_code text not null check (btrim(rule_code) <> ''),
  rule_kind text not null check (rule_kind in (
    'min_earned_credits_for_course', 'sequenced_courses',
    'mandatory_zero_credit_course', 'minimum_gpa', 'remedial_course',
    'residency_requirement', 'internship_requirement'
  )),
  provenance text not null check (btrim(provenance) <> ''),
  source_reference text check (source_reference is null or btrim(source_reference) <> ''),
  minimum_credits numeric(6,2) check (minimum_credits is null or minimum_credits >= 0),
  minimum_gpa numeric(5,3) check (minimum_gpa is null or minimum_gpa >= 0),
  rule_order integer not null default 0 check (rule_order >= 0),
  created_at timestamptz not null default now(),
  unique (policy_version_id, rule_code),
  unique (id, policy_version_id),
  check (
    rule_kind <> 'min_earned_credits_for_course'
    or minimum_credits is not null
  ),
  check (rule_kind <> 'minimum_gpa' or minimum_gpa is not null)
);

create table public.graduation_policy_rule_courses (
  policy_rule_id uuid not null references public.graduation_policy_rules(id) on delete restrict,
  course_id uuid not null references public.courses(id) on delete restrict,
  sequence_order integer check (sequence_order is null or sequence_order >= 1),
  role text not null default 'target' check (role in ('target', 'sequence', 'mandatory', 'remedial', 'internship')),
  primary key (policy_rule_id, course_id, role)
);

create table public.graduation_policy_audit_events (
  id uuid primary key default gen_random_uuid(),
  policy_version_id uuid not null references public.graduation_policy_versions(id) on delete restrict,
  event_type text not null check (event_type in ('created', 'validated', 'approved', 'retired')),
  actor_user_id uuid,
  evidence text not null check (btrim(evidence) <> ''),
  created_at timestamptz not null default now()
);

create or replace function public.validate_graduation_policy_scope()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if not exists (
    select 1 from public.graduation_policy_versions pv
    join public.graduation_policy_packages pp on pp.id = pv.policy_package_id
    where pv.id = new.policy_version_id and pp.university_id = new.university_id
  ) then
    raise exception 'graduation policy version is outside university';
  end if;
  if new.faculty_id is not null and not exists (
    select 1 from public.faculties f
    where f.id = new.faculty_id and f.university_id = new.university_id
  ) then
    raise exception 'graduation policy faculty scope is outside university';
  end if;
  if new.major_id is not null and not exists (
    select 1 from public.majors m join public.faculties f on f.id = m.faculty_id
    where m.id = new.major_id and f.university_id = new.university_id
  ) then
    raise exception 'graduation policy program scope is outside university';
  end if;
  if new.study_plan_id is not null and not exists (
    select 1 from public.study_plans sp
    join public.majors m on m.id = sp.major_id
    join public.faculties f on f.id = m.faculty_id
    where sp.id = new.study_plan_id and f.university_id = new.university_id
  ) then
    raise exception 'graduation policy study-plan scope is outside university';
  end if;
  return new;
end;
$$;

create or replace function public.enforce_graduation_policy_version_lifecycle()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'DELETE' then
    if old.lifecycle_status in ('approved', 'retired') then
      raise exception 'approved or retired graduation policy versions are immutable';
    end if;
    return old;
  end if;

  if old.lifecycle_status = 'retired' then
    raise exception 'retired graduation policy versions are immutable';
  end if;
  if old.lifecycle_status = 'approved' and (
    new.lifecycle_status <> 'retired'
    or new.policy_package_id is distinct from old.policy_package_id
    or new.version is distinct from old.version
    or new.effective_from is distinct from old.effective_from
    or new.source_id is distinct from old.source_id
    or new.content_hash is distinct from old.content_hash
    or new.validated_at is distinct from old.validated_at
    or new.validated_by is distinct from old.validated_by
    or new.approved_at is distinct from old.approved_at
    or new.approved_by is distinct from old.approved_by
  ) then
    raise exception 'approved graduation policy versions may only be retired';
  end if;
  if not (
    (old.lifecycle_status = 'draft' and new.lifecycle_status in ('draft', 'validated'))
    or (old.lifecycle_status = 'validated' and new.lifecycle_status in ('validated', 'approved'))
    or (old.lifecycle_status = 'approved' and new.lifecycle_status = 'retired')
  ) then
    raise exception 'invalid graduation policy lifecycle transition: % -> %',
      old.lifecycle_status, new.lifecycle_status;
  end if;

  if new.lifecycle_status = 'approved' and old.lifecycle_status <> 'approved' then
    if new.source_id is null then
      raise exception 'approved graduation policy version requires an academic source';
    end if;
    if not exists (
      select 1 from public.graduation_policy_applicability a
      where a.policy_version_id = new.id
    ) or not exists (
      select 1 from public.graduation_policy_rules r
      where r.policy_version_id = new.id
    ) then
      raise exception 'approved graduation policy version requires applicability and rules';
    end if;

    perform pg_catalog.pg_advisory_xact_lock(
      pg_catalog.hashtextextended(new.policy_package_id::text, 0)
    );
    if exists (
      select 1
      from public.graduation_policy_versions other
      where other.policy_package_id = new.policy_package_id
        and other.id <> new.id
        and other.lifecycle_status = 'approved'
        and daterange(other.effective_from, other.effective_to, '[]')
            && daterange(new.effective_from, new.effective_to, '[]')
    ) then
      raise exception 'graduation policy package already has an overlapping approved version';
    end if;
  end if;
  return new;
end;
$$;

create or replace function public.protect_published_graduation_policy_content()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  target_version_id uuid;
  target_status text;
begin
  if tg_table_name = 'graduation_policy_packages' then
    if exists (
      select 1 from public.graduation_policy_versions v
      where v.policy_package_id = coalesce(old.id, new.id)
        and v.lifecycle_status in ('approved', 'retired')
    ) then
      raise exception 'published graduation policy package is immutable';
    end if;
    return case when tg_op = 'DELETE' then old else new end;
  end if;

  if tg_table_name = 'graduation_policy_applicability' then
    target_version_id := coalesce(old.policy_version_id, new.policy_version_id);
  elsif tg_table_name = 'graduation_policy_rules' then
    target_version_id := coalesce(old.policy_version_id, new.policy_version_id);
  elsif tg_table_name = 'graduation_policy_rule_courses' then
    select r.policy_version_id into target_version_id
    from public.graduation_policy_rules r
    where r.id = coalesce(old.policy_rule_id, new.policy_rule_id);
  end if;

  select v.lifecycle_status into target_status
  from public.graduation_policy_versions v where v.id = target_version_id;
  if target_status in ('approved', 'retired') then
    raise exception 'published graduation policy content is immutable';
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end;
$$;

create trigger validate_graduation_policy_applicability_scope
before insert or update on public.graduation_policy_applicability
for each row execute function public.validate_graduation_policy_scope();

create trigger enforce_graduation_policy_version_lifecycle_on_write
before update or delete on public.graduation_policy_versions
for each row execute function public.enforce_graduation_policy_version_lifecycle();

create trigger protect_published_graduation_policy_package
before update or delete on public.graduation_policy_packages
for each row execute function public.protect_published_graduation_policy_content();
create trigger protect_published_graduation_policy_applicability
before update or delete on public.graduation_policy_applicability
for each row execute function public.protect_published_graduation_policy_content();
create trigger protect_published_graduation_policy_rules
before update or delete on public.graduation_policy_rules
for each row execute function public.protect_published_graduation_policy_content();
create trigger protect_published_graduation_policy_rule_courses
before update or delete on public.graduation_policy_rule_courses
for each row execute function public.protect_published_graduation_policy_content();

create index ix_graduation_policy_applicability_plan
  on public.graduation_policy_applicability (study_plan_id)
  where study_plan_id is not null;
create index ix_graduation_policy_rules_version
  on public.graduation_policy_rules (policy_version_id, rule_order);

alter table public.graduation_policy_packages enable row level security;
alter table public.graduation_policy_versions enable row level security;
alter table public.graduation_policy_applicability enable row level security;
alter table public.graduation_policy_rules enable row level security;
alter table public.graduation_policy_rule_courses enable row level security;
alter table public.graduation_policy_audit_events enable row level security;

revoke all on table public.graduation_policy_packages from public, anon, authenticated;
revoke all on table public.graduation_policy_versions from public, anon, authenticated;
revoke all on table public.graduation_policy_applicability from public, anon, authenticated;
revoke all on table public.graduation_policy_rules from public, anon, authenticated;
revoke all on table public.graduation_policy_rule_courses from public, anon, authenticated;
revoke all on table public.graduation_policy_audit_events from public, anon, authenticated;

revoke all on table public.graduation_policy_packages from service_role;
revoke all on table public.graduation_policy_versions from service_role;
revoke all on table public.graduation_policy_applicability from service_role;
revoke all on table public.graduation_policy_rules from service_role;
revoke all on table public.graduation_policy_rule_courses from service_role;
revoke all on table public.graduation_policy_audit_events from service_role;

grant select, insert, update, delete on table public.graduation_policy_packages to service_role;
grant select, insert, update, delete on table public.graduation_policy_versions to service_role;
grant select, insert, update, delete on table public.graduation_policy_applicability to service_role;
grant select, insert, update, delete on table public.graduation_policy_rules to service_role;
grant select, insert, update, delete on table public.graduation_policy_rule_courses to service_role;
grant select, insert on table public.graduation_policy_audit_events to service_role;

create trigger set_graduation_policy_packages_updated_at
before update on public.graduation_policy_packages
for each row execute function public.set_updated_at();

create trigger set_graduation_policy_versions_updated_at
before update on public.graduation_policy_versions
for each row execute function public.set_updated_at();

comment on table public.graduation_policy_versions is
  'Human-governed lifecycle: draft -> validated -> approved; only approved effective versions may drive deterministic decisions.';

revoke all on function public.validate_graduation_policy_scope() from public, anon, authenticated;
revoke all on function public.enforce_graduation_policy_version_lifecycle() from public, anon, authenticated;
revoke all on function public.protect_published_graduation_policy_content() from public, anon, authenticated;

commit;
