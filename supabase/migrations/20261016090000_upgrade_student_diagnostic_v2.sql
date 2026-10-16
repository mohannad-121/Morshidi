begin;

alter table public.student_diagnostic_responses
  add column response_time_ms integer not null default 0
    check (response_time_ms between 0 and 1800000),
  add column self_confidence text not null default 'MEDIUM'
    check (self_confidence in ('LOW', 'MEDIUM', 'HIGH'));

alter table public.student_diagnostic_skill_results
  add column reasoning_patterns text[] not null default '{}'::text[];

alter table public.student_diagnostic_sessions
  drop constraint if exists student_diagnostic_sessions_question_count_check,
  add constraint student_diagnostic_sessions_question_count_check
    check (question_count between 0 and 30);

alter table public.student_diagnostic_responses
  drop constraint if exists student_diagnostic_responses_response_order_check,
  drop constraint if exists student_diagnostic_responses_domain_check,
  add constraint student_diagnostic_responses_response_order_check
    check (response_order between 1 and 30),
  add constraint student_diagnostic_responses_domain_check check (domain in (
    'PROGRAMMING_REASONING', 'LOGICAL_PROBLEM_SOLVING', 'QUANTITATIVE_MATH',
    'STATISTICS_DATA_REASONING', 'THEORY_COMPREHENSION_MEMORY',
    'THEORY_CONCEPTUAL_UNDERSTANDING'));

alter table public.student_diagnostic_skill_results
  drop constraint if exists student_diagnostic_skill_results_domain_check,
  drop constraint if exists student_diagnostic_skill_results_response_count_check,
  add constraint student_diagnostic_skill_results_domain_check check (domain in (
    'PROGRAMMING_REASONING', 'LOGICAL_PROBLEM_SOLVING', 'QUANTITATIVE_MATH',
    'STATISTICS_DATA_REASONING', 'THEORY_COMPREHENSION_MEMORY',
    'THEORY_CONCEPTUAL_UNDERSTANDING')),
  add constraint student_diagnostic_skill_results_response_count_check
    check (response_count between 1 and 6);

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
  if s.assessment_version <> 'QUICK_DIAGNOSTIC_V1' then
    raise exception 'unsupported diagnostic assessment version' using errcode = '22023';
  end if;
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

create function public.record_student_diagnostic_answer(
  p_session_id uuid, p_owner_user_id uuid, p_question_id text,
  p_selected_option text, p_domain text, p_difficulty text, p_is_correct boolean,
  p_response_time_ms integer, p_self_confidence text,
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
     or p_response_time_ms is null or p_response_time_ms not between 0 and 1800000
     or p_self_confidence is null or p_self_confidence not in ('LOW', 'MEDIUM', 'HIGH')
     or p_domain is null or p_domain not in (
       'PROGRAMMING_REASONING', 'LOGICAL_PROBLEM_SOLVING', 'QUANTITATIVE_MATH',
       'STATISTICS_DATA_REASONING', 'THEORY_CONCEPTUAL_UNDERSTANDING')
     or p_difficulty is null or p_difficulty not in ('EASY', 'MEDIUM', 'HARD')
     or (p_next_question_id is not null
         and pg_catalog.length(p_next_question_id) not between 3 and 32) then
    raise exception 'invalid diagnostic answer arguments' using errcode = '22023';
  end if;

  select * into s from public.student_diagnostic_sessions
   where id = p_session_id and owner_user_id = p_owner_user_id for update;
  if not found then
    raise exception 'diagnostic session not found' using errcode = 'P0002';
  end if;
  if s.assessment_version <> 'QUICK_DIAGNOSTIC_V2' then
    raise exception 'unsupported diagnostic assessment version' using errcode = '22023';
  end if;
  if s.status <> 'IN_PROGRESS' or s.current_question_id <> p_question_id then
    raise exception 'question is not currently issued' using errcode = '55000';
  end if;

  select pg_catalog.count(*) into actual_response_count
    from public.student_diagnostic_responses r where r.session_id = s.id;
  if actual_response_count <> s.question_count then
    raise exception 'diagnostic session response count mismatch' using errcode = '55000';
  end if;
  next_order := s.question_count + 1;
  if next_order > 30 then
    raise exception 'diagnostic maximum question count exceeded' using errcode = '22023';
  end if;
  if p_next_question_id is null and next_order <> 30 then
    raise exception 'diagnostic completion requires exactly 30 answers' using errcode = '22023';
  elsif p_next_question_id is not null then
    if next_order >= 30 then
      raise exception 'diagnostic question 30 must complete the assessment' using errcode = '22023';
    end if;
    if p_next_question_id = p_question_id or exists (
      select 1 from public.student_diagnostic_responses r
       where r.session_id = s.id and r.question_id = p_next_question_id
    ) then
      raise exception 'diagnostic next question must be unanswered' using errcode = '22023';
    end if;
    if p_results is not null then
      raise exception 'diagnostic continuation must not include results' using errcode = '22023';
    end if;
  end if;

  insert into public.student_diagnostic_responses(
    session_id, question_id, selected_option, domain, difficulty, is_correct,
    response_time_ms, self_confidence, response_order)
  values (s.id, p_question_id, p_selected_option, p_domain, p_difficulty, p_is_correct,
          p_response_time_ms, p_self_confidence, next_order);

  if p_next_question_id is null then
    if p_results is null or pg_catalog.jsonb_typeof(p_results) <> 'array'
       or pg_catalog.jsonb_array_length(p_results) <> 5 then
      raise exception 'completed assessment requires five results' using errcode = '22023';
    end if;
    select pg_catalog.count(distinct result->>'domain') into result_domain_count
      from pg_catalog.jsonb_array_elements(p_results) as results(result);
    if result_domain_count <> 5 then
      raise exception 'completed assessment requires five unique domains' using errcode = '22023';
    end if;
    for item in select value from pg_catalog.jsonb_array_elements(p_results) loop
      if pg_catalog.jsonb_typeof(item) is distinct from 'object'
         or item->>'domain' not in (
           'PROGRAMMING_REASONING', 'LOGICAL_PROBLEM_SOLVING', 'QUANTITATIVE_MATH',
           'STATISTICS_DATA_REASONING', 'THEORY_CONCEPTUAL_UNDERSTANDING')
         or item->>'score' is null or item->>'score' !~ '^(0|[1-9][0-9]?|100)$'
         or item->>'confidence' not in ('LOW', 'MEDIUM', 'HIGH')
         or item->>'response_count' is distinct from '6'
         or pg_catalog.jsonb_typeof(item->'reason_codes') is distinct from 'array'
         or pg_catalog.jsonb_typeof(item->'reasoning_patterns') is distinct from 'array'
         or item->>'scoring_policy_version' is distinct from 'DIAGNOSTIC_SCORING_V2' then
        raise exception 'invalid diagnostic result arguments' using errcode = '22023';
      end if;
      if exists (
        select 1 from pg_catalog.jsonb_array_elements_text(item->'reason_codes') reason
         where reason not in (
           'MODELED_DIAGNOSTIC_BASELINE', 'VALID_RESPONSES_6', 'FULL_DIFFICULTY_COVERAGE',
           'INCOMPLETE_RESPONSES', 'UNREALISTICALLY_FAST', 'REPETITIVE_OPTION_PATTERN',
           'CONTRADICTORY_PERFORMANCE', 'RANDOM_LOOKING_PATTERN')
      ) or exists (
        select 1 from pg_catalog.jsonb_array_elements_text(item->'reasoning_patterns') pattern
         where pattern not in (
           'STRONG_SYSTEMATIC_REASONING', 'CAREFUL_BUT_SLOWER', 'FAST_BUT_ERROR_PRONE',
           'SELF_CONFIDENCE_ABOVE_EVIDENCE', 'SELF_CONFIDENCE_BELOW_PERFORMANCE',
           'DIFFICULTY_WITH_MULTI_STEP_PROBLEMS')
      ) or not (item->'reason_codes' ? 'MODELED_DIAGNOSTIC_BASELINE')
        or not (item->'reason_codes' ? 'VALID_RESPONSES_6')
        or not (item->'reason_codes' ? 'FULL_DIFFICULTY_COVERAGE')
        or (select pg_catalog.count(*) from pg_catalog.jsonb_array_elements_text(item->'reason_codes'))
           <> (select pg_catalog.count(distinct reason)
                 from pg_catalog.jsonb_array_elements_text(item->'reason_codes') reason)
        or (select pg_catalog.count(*) from pg_catalog.jsonb_array_elements_text(item->'reasoning_patterns'))
           <> (select pg_catalog.count(distinct pattern)
                 from pg_catalog.jsonb_array_elements_text(item->'reasoning_patterns') pattern) then
        raise exception 'invalid diagnostic bounded evidence codes' using errcode = '22023';
      end if;
      select pg_catalog.count(*) into actual_response_count
        from public.student_diagnostic_responses r
       where r.session_id = s.id and r.domain = item->>'domain';
      if actual_response_count <> 6 then
        raise exception 'each diagnostic domain requires six responses' using errcode = '22023';
      end if;
      if exists (
        select 1 from (values ('EASY'), ('MEDIUM'), ('HARD')) expected(difficulty)
         where (select pg_catalog.count(*) from public.student_diagnostic_responses r
                where r.session_id=s.id and r.domain=item->>'domain'
                  and r.difficulty=expected.difficulty) <> 2
      ) then
        raise exception 'each domain requires two responses per difficulty' using errcode = '22023';
      end if;
      result_response_total := result_response_total + 6;
      insert into public.student_diagnostic_skill_results(
        session_id, domain, score, confidence, response_count, reason_codes,
        reasoning_patterns, scoring_policy_version)
      values (s.id, item->>'domain', (item->>'score')::integer, item->>'confidence', 6,
              array(select pg_catalog.jsonb_array_elements_text(item->'reason_codes')),
              array(select pg_catalog.jsonb_array_elements_text(item->'reasoning_patterns')),
              item->>'scoring_policy_version');
    end loop;
    if result_response_total <> 30 then
      raise exception 'diagnostic result counts must equal 30' using errcode = '22023';
    end if;
    update public.student_diagnostic_sessions set status='COMPLETED', current_question_id=null,
      question_count=30, completed_at=pg_catalog.now(), updated_at=pg_catalog.now()
      where id=s.id returning * into s;
  else
    update public.student_diagnostic_sessions set current_question_id=p_next_question_id,
      question_count=next_order, updated_at=pg_catalog.now() where id=s.id returning * into s;
  end if;
  return s;
end $$;

revoke all on function public.record_student_diagnostic_answer(
  uuid,uuid,text,text,text,text,boolean,text,jsonb)
  from public, anon, authenticated, service_role;
grant execute on function public.record_student_diagnostic_answer(
  uuid,uuid,text,text,text,text,boolean,text,jsonb)
  to service_role;

revoke all on function public.record_student_diagnostic_answer(
  uuid,uuid,text,text,text,text,boolean,integer,text,text,jsonb)
  from public, anon, authenticated, service_role;
grant execute on function public.record_student_diagnostic_answer(
  uuid,uuid,text,text,text,text,boolean,integer,text,text,jsonb)
  to service_role;

commit;
