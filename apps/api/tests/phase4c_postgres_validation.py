"""Local-only Phase 4C SQL checks against a disposable, network-disabled container.

Create phase4c_morshidi as an empty database first. This script installs a minimal
universities fixture and the two notification migrations, then writes synthetic data.
"""
import json
import subprocess
import unittest
from pathlib import Path

CONTAINER = 'morshidi-phase4b-disposable'
DATABASE = 'phase4c_morshidi'
ROOT = Path(__file__).resolve().parents[3]
A = '11111111-1111-1111-1111-111111111111'
B = '22222222-2222-2222-2222-222222222222'

def sql(query, check=True):
    result = subprocess.run(['docker', 'exec', '-i', CONTAINER, 'psql', '-X', '-q', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-U', 'postgres', '-d', DATABASE], input=query, text=True, capture_output=True, encoding='utf-8')
    if check and result.returncode: raise AssertionError(result.stderr)
    return result.stdout.strip() if check else result

def event(eid, kind='registration.opened', student=None, version=1, key='same-key'):
    data = {'id': eid, 'type': kind, 'version': version, 'occurredAt': '2026-10-21T00:00:00Z', 'studentId': student, 'payload': {}, 'idempotencyKey': key}
    return json.dumps(data, separators=(',', ':'))

def ingest(university, body):
    return json.loads(sql(f"set role service_role; select public.ingest_university_event_scoped('{university}', '{body}'::jsonb)"))

class ScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mode = subprocess.check_output(['docker', 'inspect', '--format', '{{.HostConfig.NetworkMode}}', CONTAINER], text=True).strip()
        if mode != 'none': raise RuntimeError('Requires network-isolated disposable container')
        sql('create table public.universities(id uuid primary key, active boolean not null default true);')
        sql(f"insert into public.universities(id) values ('{A}'),('{B}');")
        sql((ROOT / 'supabase/migrations/20261004090000_university_live_sync.sql').read_text(encoding='utf-8'))
        sql("select public.ingest_university_event('" + event('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', key='legacy') + "'::jsonb)")
        migration = next((ROOT / 'supabase/migrations').glob('*_university_scoped_notifications.sql'))
        sql(migration.read_text(encoding='utf-8'))

    def test_scope_and_versions(self):
        common = event('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb')
        self.assertTrue(ingest(A, common)['applied'])
        self.assertTrue(ingest(B, common)['applied'])
        self.assertTrue(ingest(A, common)['duplicate'])
        self.assertTrue(ingest(A, event('cccccccc-cccc-cccc-cccc-cccccccccccc','grade.posted','123456789', key='private'))['applied'])
        self.assertTrue(ingest(B, event('dddddddd-dddd-dddd-dddd-dddddddddddd','grade.posted','123456789', key='private'))['applied'])
        self.assertEqual(sql(f"select count(*) from public.student_notifications where university_id='{A}' and (student_id='123456789' or student_id is null)"), '2')
        self.assertEqual(sql(f"select count(*) from public.student_notifications where university_id='{B}' and (student_id='123456789' or student_id is null)"), '2')
        self.assertEqual(sql(f"select count(*) from public.student_notifications where university_id='{A}' and (student_id='999999999' or student_id is null)"), '1')
        self.assertEqual(sql("select count(*) from public.student_notifications where university_id is null"), '1')
        self.assertEqual(sql("select count(*) from public.university_event_versions where aggregate_key='calendar' and university_id is not null"), '2')
        self.assertFalse(ingest(A, event('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',version=1,key='stale'))['applied'])
        self.assertTrue(ingest(B, event('ffffffff-ffff-ffff-ffff-ffffffffffff',version=2,key='new'))['applied'])
        self.assertNotEqual(sql("set role service_role; select public.ingest_university_event_scoped(null,'{}'::jsonb)",False).returncode, 0)
        self.assertNotEqual(sql("set role service_role; select public.ingest_university_event_scoped('99999999-9999-9999-9999-999999999999','{}'::jsonb)",False).returncode, 0)

    def test_privileges(self):
        for role in ('anon', 'authenticated'):
            self.assertNotEqual(sql(f'set role {role}; select * from public.student_notifications',False).returncode, 0)
            self.assertNotEqual(sql(f"set role {role}; select public.ingest_university_event_scoped('{A}','{{}}'::jsonb)",False).returncode, 0)
        self.assertNotEqual(sql("set role service_role; select public.ingest_university_event('{}'::jsonb)",False).returncode,0)

if __name__ == '__main__': unittest.main(verbosity=2)
