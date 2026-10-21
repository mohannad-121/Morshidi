"""Upgrade a populated, disposable Phase 4D Supabase stack; run once only."""
import json
import subprocess
from pathlib import Path
from uuid import uuid4

CONTAINER = 'supabase_db_MorshidiPhase4DUpgrade'
ROOT = Path(__file__).resolve().parents[3]

def sql(statement, check=True):
    r = subprocess.run(['docker','exec','-i',CONTAINER,'psql','-X','-q','-A','-t','-v','ON_ERROR_STOP=1','-U','postgres','-d','postgres'],input=statement,text=True,encoding='utf-8',capture_output=True)
    if check and r.returncode: raise AssertionError(r.stderr)
    return r.stdout.strip() if check else r

# The original RPC and tables must exist and the new column must not.
assert sql("select count(*) from information_schema.columns where table_schema='public' and table_name='student_notifications' and column_name='university_id'") == '0'
a,b,eid = str(uuid4()),str(uuid4()),str(uuid4())
sql(f"insert into public.universities(id,name_ar,country,tenant_key) values ('{a}','Synthetic A','test','{a}'),('{b}','Synthetic B','test','{b}');")
event = {'id': eid, 'type': 'registration.opened', 'version': 1, 'occurredAt': '2026-10-21T00:00:00Z', 'payload': {}, 'idempotencyKey': 'old-key'}
body = json.dumps(event, separators=(',', ':'))
assert json.loads(sql(f"select public.ingest_university_event('{body}'::jsonb)"))['applied']
assert sql('select count(*) from public.student_notifications') == '1'
migration = (ROOT / 'supabase/migrations/20261021162616_university_scoped_notifications.sql').read_text(encoding='utf-8')
sql(migration)
assert sql('select count(*) from public.student_notifications where university_id is null') == '1'
assert sql('select count(*) from public.university_event_inbox where university_id is null') == '1'
assert sql('select count(*) from public.university_event_versions where university_id is null') == '1'
for uni in (a,b):
    assert json.loads(sql(f"set role service_role; select public.ingest_university_event_scoped('{uni}','{body}'::jsonb)"))['applied']
    assert json.loads(sql(f"set role service_role; select public.ingest_university_event_scoped('{uni}','{body}'::jsonb)"))['duplicate']
assert sql("select count(*) from public.university_event_versions where university_id is not null and aggregate_key='calendar'") == '2'
assert sql('select count(*) from public.student_notifications where university_id is not null') == '2'
assert sql("select count(*) from pg_indexes where indexname='student_notifications_university_scope_created_idx'") == '1'
assert sql("select count(*) from pg_constraint where conname in ('student_notifications_scoped_event_fk','university_event_inbox_scope_idempotency_key','university_event_versions_scope_key')") == '3'
assert sql("select bool_and(relrowsecurity and relforcerowsecurity) from pg_class where oid in ('public.student_notifications'::regclass,'public.university_event_inbox'::regclass,'public.university_event_versions'::regclass)") == 't'
for role in ('anon','authenticated'):
    assert sql(f"set role {role}; select * from public.student_notifications",False).returncode != 0
    assert sql(f"set role {role}; select public.ingest_university_event_scoped('{a}','{body}'::jsonb)",False).returncode != 0
assert sql(f"set role service_role; select public.ingest_university_event('{body}'::jsonb)",False).returncode != 0
print('Upgrade validation passed: legacy quarantine, scoped deduplication and versions, indexes, constraints, RLS and grants.')
