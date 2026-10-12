-- Student Intelligence V2: server-authoritative quick diagnostic persistence.
-- Forward-only migration. Created for review; intentionally not applied here.

begin;

create table public.student_diagnostic_sessions (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  profile_id uuid not null references public.student_academic_profiles(id) on delete cascade,
  institution_id uuid not null references public.universities(id) on delete restrict,
  study_plan_id uuid not null references public.study_plans(id) on delete restrict,
  assessment_version text not null,
  status text not null check (status in ('IN_PROGRESS', 'COMPLETED', 'ABANDONED')),
  current_question_id text,
  question_count integer not null default 0 check (question_count between 0 and 16),
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check ((status = 'IN_PROGRESS' and completed_at is null and current_question_id is not null)
      or (status <> 'IN_PROGRESS' and current_question_id is null)),
  check ((status = 'COMPLETED' and completed_at is not null) or status <> 'COMPLETED')
);

create unique index student_diagnostic_one_active_idx
  on public.student_diagnostic_sessions(owner_user_id, study_plan_id, assessment_version)
  where status = 'IN_PROGRESS';
create index student_diagnostic_owner_idx
  on public.student_diagnostic_sessions(owner_user_id, institution_id, created_at desc);

create table public.student_diagnostic_responses (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.student_diagnostic_sessions(id) on delete cascade,
  question_id text not null,
  selected_option text not null check (selected_option ~ '^[A-D]$'),
  domain text not null check (domain in (
    'PROGRAMMING_REASONING', 'LOGICAL_PROBLEM_SOLVING', 'QUANTITATIVE_MATH',
    'STATISTICS_DATA_REASONING', 'THEORY_COMPREHENSION_MEMORY')),
  difficulty text not null check (difficulty in ('EASY', 'MEDIUM', 'HARD')),
  is_correct boolean not null,
  response_order integer not null check (response_order between 1 and 16),
  answered_at timestamptz not null default now(),
  unique(session_id, question_id),
  unique(session_id, response_order)
);

create index student_diagnostic_response_session_idx
  on public.student_diagnostic_responses(session_id, response_order);

create table public.student_diagnostic_skill_results (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.student_diagnostic_sessions(id) on delete cascade,
  domain text not null check (domain in (
    'PROGRAMMING_REASONING', 'LOGICAL_PROBLEM_SOLVING', 'QUANTITATIVE_MATH',
    'STATISTICS_DATA_REASONING', 'THEORY_COMPREHENSION_MEMORY')),
  score integer not null check (score between 0 and 100),
  confidence text not null check (confidence in ('LOW', 'MEDIUM', 'HIGH')),
  response_count integer not null check (response_count between 1 and 5),
  reason_codes text[] not null default '{}',
  scoring_policy_version text not null,
  created_at timestamptz not null default now(),
  unique(session_id, domain)
);

alter table public.student_diagnostic_sessions owner to postgres;
alter table public.student_diagnostic_responses owner to postgres;
alter table public.student_diagnostic_skill_results owner to postgres;

create or replace function public.validate_student_diagnostic_scope()
returns trigger language plpgsql security definer
set search_path = '' as $$
declare actual_owner uuid; actual_plan uuid; actual_institution uuid;
begin
  select p.owner_user_id, p.study_plan_id, f.university_id
    into actual_owner, actual_plan, actual_institution
    from public.student_academic_profiles p
    join public.study_plans sp on sp.id = p.study_plan_id
    join public.majors m on m.id = sp.major_id
    join public.faculties f on f.id = m.faculty_id
   where p.id = new.profile_id;
  if actual_owner is null or actual_owner <> new.owner_user_id
     or actual_plan <> new.study_plan_id or actual_institution <> new.institution_id then
    raise exception 'diagnostic scope mismatch' using errcode = '23514';
  end if;
  new.updated_at := pg_catalog.now();
  return new;
end $$;

create trigger student_diagnostic_scope_guard
before insert or update on public.student_diagnostic_sessions
for each row execute function public.validate_student_diagnostic_scope();

create or replace function public.prevent_completed_diagnostic_mutation()
returns trigger language plpgsql set search_path = '' as $$
begin
  if old.status in ('COMPLETED', 'ABANDONED') then
    raise exception 'closed diagnostic session is immutable' using errcode = '55000';
  end if;
  return new;
end $$;

create trigger student_diagnostic_closed_guard
before update on public.student_diagnostic_sessions
for each row execute function public.prevent_completed_diagnostic_mutation();

create or replace function public.prevent_diagnostic_child_mutation()
returns trigger language plpgsql security definer
set search_path = '' as $$
declare session_status text; issued_question text;
begin
  if tg_op <> 'INSERT' then
    raise exception 'diagnostic evidence is immutable' using errcode = '55000';
  end if;
  select s.status, s.current_question_id into session_status, issued_question
    from public.student_diagnostic_sessions s where s.id = new.session_id for update;
  if session_status is distinct from 'IN_PROGRESS' then
    raise exception 'diagnostic session is not writable' using errcode = '55000';
  end if;
  if tg_table_name = 'student_diagnostic_responses' then
    if issued_question is distinct from new.question_id then
      raise exception 'question is not currently issued' using errcode = '55000';
    end if;
  end if;
  return new;
end $$;

create trigger student_diagnostic_response_immutability
before insert or update or delete on public.student_diagnostic_responses
for each row execute function public.prevent_diagnostic_child_mutation();

create trigger student_diagnostic_result_immutability
before insert or update or delete on public.student_diagnostic_skill_results
for each row execute function public.prevent_diagnostic_child_mutation();

create or replace function public.record_student_diagnostic_answer(
  p_session_id uuid, p_owner_user_id uuid, p_question_id text,
  p_selected_option text, p_domain text, p_difficulty text, p_is_correct boolean,
  p_next_question_id text, p_results jsonb default null
) returns public.student_diagnostic_sessions
language plpgsql security definer
set search_path = '' as $$
declare
  s public.student_diagnostic_sessions;
  item jsonb;
  next_order integer;
  result_domain_count integer;
  result_response_total integer := 0;
  actual_response_count integer;
begin
  if p_question_id is null or pg_catalog.length(p_question_id) not between 3 and 32
     or p_selected_option is null or p_selected_option !~ '^[A-D]$'
     or p_is_correct is null
     or p_domain is null or p_domain not in ('PROGRAMMING_REASONING', 'LOGICAL_PROBLEM_SOLVING',
       'QUANTITATIVE_MATH', 'STATISTICS_DATA_REASONING', 'THEORY_COMPREHENSION_MEMORY')
     or p_difficulty is null or p_difficulty not in ('EASY', 'MEDIUM', 'HARD')
     or (p_next_question_id is not null
         and pg_catalog.length(p_next_question_id) not between 3 and 32) then
    raise exception 'invalid diagnostic answer arguments' using errcode = '22023';
  end if;
  select * into s from public.student_diagnostic_sessions
   where id = p_session_id and owner_user_id = p_owner_user_id for update;
  if not found then raise exception 'diagnostic session not found' using errcode = 'P0002'; end if;
  if s.status <> 'IN_PROGRESS' or s.current_question_id <> p_question_id then
    raise exception 'question is not currently issued' using errcode = '55000';
  end if;
  select pg_catalog.count(*) into actual_response_count
    from public.student_diagnostic_responses r where r.session_id = s.id;
  if actual_response_count <> s.question_count then
    raise exception 'diagnostic session response count mismatch' using errcode = '55000';
  end if;
  next_order := s.question_count + 1;
  if next_order > 16 then
    raise exception 'diagnostic maximum question count exceeded' using errcode = '22023';
  end if;
  if p_next_question_id is null then
    if next_order < 10 or next_order > 16 then
      raise exception 'diagnostic completion requires 10 to 16 answers' using errcode = '22023';
    end if;
  else
    if next_order >= 16 then
      raise exception 'diagnostic question 16 must complete the assessment' using errcode = '22023';
    end if;
    if p_next_question_id = p_question_id then
      raise exception 'diagnostic next question must differ from current question' using errcode = '22023';
    end if;
    if exists (
      select 1 from public.student_diagnostic_responses r
       where r.session_id = s.id and r.question_id = p_next_question_id
    ) then
      raise exception 'diagnostic next question was already answered' using errcode = '22023';
    end if;
    if p_results is not null then
      raise exception 'diagnostic continuation must not include results' using errcode = '22023';
    end if;
  end if;
  insert into public.student_diagnostic_responses(
    session_id, question_id, selected_option, domain, difficulty, is_correct, response_order)
  values (s.id, p_question_id, p_selected_option, p_domain, p_difficulty, p_is_correct, next_order);
  if p_next_question_id is null then
    if p_results is null or pg_catalog.jsonb_typeof(p_results) <> 'array'
       or pg_catalog.jsonb_array_length(p_results) <> 5 then
      raise exception 'completed assessment requires results' using errcode = '22023';
    end if;
    select pg_catalog.count(distinct result->>'domain') into result_domain_count
      from pg_catalog.jsonb_array_elements(p_results) as results(result);
    if result_domain_count <> 5 then
      raise exception 'completed assessment requires five unique domains' using errcode = '22023';
    end if;
    for item in select value from pg_catalog.jsonb_array_elements(p_results) loop
      if pg_catalog.jsonb_typeof(item) is distinct from 'object'
         or item->>'domain' is null
         or item->>'domain' not in ('PROGRAMMING_REASONING', 'LOGICAL_PROBLEM_SOLVING',
           'QUANTITATIVE_MATH', 'STATISTICS_DATA_REASONING', 'THEORY_COMPREHENSION_MEMORY')
         or item->>'score' is null or item->>'score' !~ '^(0|[1-9][0-9]?|100)$'
         or item->>'confidence' is null or item->>'confidence' not in ('LOW', 'MEDIUM', 'HIGH')
         or item->>'response_count' is null or item->>'response_count' !~ '^[1-5]$'
         or pg_catalog.jsonb_typeof(item->'reason_codes') is distinct from 'array'
         or pg_catalog.jsonb_array_length(item->'reason_codes') not between 2 and 4
         or item->>'scoring_policy_version' is distinct from 'DIAGNOSTIC_SCORING_V1' then
        raise exception 'invalid diagnostic result arguments' using errcode = '22023';
      end if;
      if exists (
        select 1 from pg_catalog.jsonb_array_elements_text(item->'reason_codes') as reasons(reason)
         where reason not in (
           'MODELED_DIAGNOSTIC_BASELINE', 'RESPONSES_1', 'RESPONSES_2', 'RESPONSES_3',
           'RESPONSES_4', 'RESPONSES_5', 'LIMITED_ITEM_COUNT', 'MIXED_RESPONSE_PATTERN'
         )
      ) or (
        select pg_catalog.count(*)
          from pg_catalog.jsonb_array_elements_text(item->'reason_codes') as reasons(reason)
      ) <> (
        select pg_catalog.count(distinct reason)
          from pg_catalog.jsonb_array_elements_text(item->'reason_codes') as reasons(reason)
      ) or not (item->'reason_codes' ? 'MODELED_DIAGNOSTIC_BASELINE')
        or not (item->'reason_codes' ? ('RESPONSES_' || (item->>'response_count'))) then
        raise exception 'invalid diagnostic reason codes' using errcode = '22023';
      end if;
      select pg_catalog.count(*) into actual_response_count
        from public.student_diagnostic_responses r
       where r.session_id = s.id and r.domain = item->>'domain';
      if actual_response_count <> (item->>'response_count')::integer then
        raise exception 'diagnostic result response count mismatch' using errcode = '22023';
      end if;
      result_response_total := result_response_total + (item->>'response_count')::integer;
      insert into public.student_diagnostic_skill_results(
        session_id, domain, score, confidence, response_count, reason_codes, scoring_policy_version)
      values (s.id, item->>'domain', (item->>'score')::integer, item->>'confidence',
              (item->>'response_count')::integer,
              array(select pg_catalog.jsonb_array_elements_text(item->'reason_codes')),
              item->>'scoring_policy_version');
    end loop;
    if result_response_total <> next_order then
      raise exception 'diagnostic result response counts must equal answer count' using errcode = '22023';
    end if;
    update public.student_diagnostic_sessions set status='COMPLETED', current_question_id=null,
      question_count=next_order, completed_at=pg_catalog.now(), updated_at=pg_catalog.now()
      where id=s.id returning * into s;
  else
    update public.student_diagnostic_sessions set current_question_id=p_next_question_id,
      question_count=next_order, updated_at=pg_catalog.now() where id=s.id returning * into s;
  end if;
  return s;
end $$;

alter table public.student_diagnostic_sessions enable row level security;
alter table public.student_diagnostic_responses enable row level security;
alter table public.student_diagnostic_skill_results enable row level security;

revoke all on public.student_diagnostic_sessions from anon, authenticated, service_role;
revoke all on public.student_diagnostic_responses from anon, authenticated, service_role;
revoke all on public.student_diagnostic_skill_results from anon, authenticated, service_role;
revoke all on function public.validate_student_diagnostic_scope()
  from public, anon, authenticated, service_role;
revoke all on function public.prevent_completed_diagnostic_mutation()
  from public, anon, authenticated, service_role;
revoke all on function public.prevent_diagnostic_child_mutation()
  from public, anon, authenticated, service_role;
revoke all on function public.record_student_diagnostic_answer(uuid,uuid,text,text,text,text,boolean,text,jsonb)
  from public, anon, authenticated, service_role;
grant select, insert on public.student_diagnostic_sessions to service_role;
grant update(status, current_question_id, updated_at)
  on public.student_diagnostic_sessions to service_role;
grant select on public.student_diagnostic_responses to service_role;
grant select on public.student_diagnostic_skill_results to service_role;
grant execute on function public.record_student_diagnostic_answer(uuid,uuid,text,text,text,text,boolean,text,jsonb)
  to service_role;

commit;
