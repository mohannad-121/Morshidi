begin;
-- Historical rows have unknown provenance. NULL university_id quarantines them;
-- never infer their owner from the currently configured integration.
alter table public.university_event_inbox add column university_id uuid references public.universities(id);
alter table public.university_event_versions add column university_id uuid references public.universities(id);
alter table public.student_notifications add column university_id uuid references public.universities(id);
alter table public.student_notifications drop constraint student_notifications_event_id_fkey;
alter table public.student_notifications drop constraint student_notifications_event_id_student_id_key;
alter table public.university_event_inbox drop constraint university_event_inbox_pkey;
alter table public.university_event_inbox drop constraint university_event_inbox_idempotency_key_key;
alter table public.university_event_versions drop constraint university_event_versions_pkey;
alter table public.university_event_inbox add constraint university_event_inbox_scope_event_key unique (university_id,event_id);
alter table public.university_event_inbox add constraint university_event_inbox_scope_idempotency_key unique (university_id,idempotency_key);
alter table public.university_event_versions add constraint university_event_versions_scope_key unique (university_id,aggregate_key);
alter table public.student_notifications add constraint student_notifications_scoped_event_fk foreign key (university_id,event_id) references public.university_event_inbox(university_id,event_id) on delete cascade;
alter table public.student_notifications add constraint student_notifications_scoped_event_key unique (university_id,event_id,student_id);
create index student_notifications_university_scope_created_idx on public.student_notifications (university_id, student_id, created_at desc, id desc);
-- Prevent old application versions from adding events without authoritative scope.
revoke all on function public.ingest_university_event(jsonb) from public, anon, authenticated, service_role;
grant select (id, active) on public.universities to service_role;
create or replace function public.ingest_university_event_scoped(p_university_id uuid, p_event jsonb)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_id uuid := (p_event ->> 'id')::uuid;
  v_key text := p_event ->> 'idempotencyKey';
  v_type text := p_event ->> 'type';
  v_version bigint := (p_event ->> 'version')::bigint;
  v_occurred timestamptz := (p_event ->> 'occurredAt')::timestamptz;
  v_student text := nullif(p_event ->> 'studentId', '');
  v_payload jsonb := coalesce(p_event -> 'payload', '{}'::jsonb);
  v_aggregate text;
  v_previous bigint;
  v_inserted integer;
  v_summary text;
begin
  if p_university_id is null or not exists (select 1 from public.universities where id = p_university_id and active) then
    raise exception 'invalid university scope' using errcode = '22023';
  end if;
  if v_id is null or v_key is null or btrim(v_key) = '' or v_type is null
     or v_version is null or v_version < 1 or v_occurred is null
     or jsonb_typeof(v_payload) <> 'object' then
    raise exception 'invalid university event' using errcode = '22023';
  end if;

  insert into public.university_event_inbox(university_id,event_id,idempotency_key,event_type,event_version,
    occurred_at,student_id,payload)
  values (p_university_id,v_id,v_key,v_type,v_version,v_occurred,v_student,v_payload)
  on conflict do nothing;
  get diagnostics v_inserted = row_count;
  if v_inserted = 0 then
    return jsonb_build_object('duplicate', true, 'applied', false);
  end if;

  v_aggregate := case
    when v_student is not null then 'student:' || v_student
    when v_type like 'registration.%' then 'calendar'
    else 'offering:' || coalesce(v_payload ->> 'sectionId', v_type)
  end;
  perform pg_advisory_xact_lock(hashtextextended(p_university_id::text || ':' || v_aggregate, 0));
  select last_version into v_previous from public.university_event_versions
    where university_id = p_university_id and aggregate_key = v_aggregate for update;
  if v_previous is not null and v_version <= v_previous then
    return jsonb_build_object('duplicate', false, 'applied', false, 'stale', true);
  end if;
  insert into public.university_event_versions(university_id,aggregate_key,last_version,occurred_at)
  values (p_university_id,v_aggregate,v_version,v_occurred)
  on conflict (university_id,aggregate_key) do update set last_version = excluded.last_version,
    occurred_at = excluded.occurred_at, updated_at = now();

  v_summary := case v_type
    when 'grade.posted' then 'نزلت علامة مادة ' || coalesce(v_payload ->> 'courseName', v_payload ->> 'courseCode', '')
    when 'registration.opened' then 'فُتح التسجيل للفصل الحالي'
    when 'registration.closed' then 'أُغلق التسجيل للفصل الحالي'
    when 'section.opened' then 'انفتحت شعبة للمادة ' || coalesce(v_payload ->> 'courseCode', '')
    when 'section.closed' then 'أُغلقت شعبة للمادة ' || coalesce(v_payload ->> 'courseCode', '')
    when 'offering.updated' then 'تحدّثت شعبة المادة ' || coalesce(v_payload ->> 'courseCode', '')
    when 'schedule.changed' then 'تحدّث جدولك الدراسي'
    when 'plan.updated' then 'تحدّثت خطتك الدراسية'
    when 'record.updated' then 'تحدّث سجلك الأكاديمي'
    else 'وصل تحديث من الجامعة'
  end;
  insert into public.student_notifications(university_id,event_id,student_id,summary)
    values (p_university_id,v_id,v_student,v_summary);
  return jsonb_build_object('duplicate', false, 'applied', true);
end;
$$;

revoke all on function public.ingest_university_event_scoped(uuid,jsonb) from public, anon, authenticated;
grant execute on function public.ingest_university_event_scoped(uuid,jsonb) to service_role;
commit;
