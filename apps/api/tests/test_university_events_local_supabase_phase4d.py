"""Opt-in local Supabase integration; requires the isolated Phase 4D stack only."""
import asyncio
import hashlib
import hmac
import json
import os
import subprocess
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from app.core.auth import CurrentUser
from app.core.config import settings
from app.university_sync.event_routes import my_university_stream, router
from app.university_sync.events import UniversityEventStore
from app.university_sync.identity_repository import SupabaseUniversityIdentityRepository

pytestmark = pytest.mark.skipif(os.getenv('MORSHIDI_PHASE4D_LOCAL') != '1', reason='requires explicitly enabled disposable local stack')


def test_authenticated_two_university_runtime(monkeypatch):
    status = subprocess.run(['supabase.cmd', 'status', '--workdir', '.phase4d_isolated', '-o', 'json'], capture_output=True, text=True, check=True)
    local = json.loads(status.stdout)
    url = local['API_URL']
    assert url == 'http://127.0.0.1:55321'
    service, anon = local['SERVICE_ROLE_KEY'], local['ANON_KEY']
    monkeypatch.setattr(settings, 'supabase_url', url)
    monkeypatch.setattr(settings, 'supabase_secret_key', SecretStr(service))
    uni_a, uni_b = str(uuid4()), str(uuid4())
    header = {'apikey': service, 'Authorization': f'Bearer {service}'}

    async def run():
        async with httpx.AsyncClient(timeout=10) as db:
            async def create_user():
                email = f'{uuid4().hex}@example.test'
                password = 'test-only-Password-1234!'
                response = await db.post(url + '/auth/v1/admin/users', headers=header, json={'email': email, 'password': password, 'email_confirm': True})
                assert response.status_code in (200, 201), response.status_code
                uid = response.json()['id']
                response = await db.post(url + '/auth/v1/token?grant_type=password', headers={'apikey': anon}, json={'email': email, 'password': password})
                assert response.status_code == 200, response.status_code
                return uid, response.json()['access_token']
            a, b, a2, missing = [await create_user() for _ in range(4)]
            universities = [{'id': uni_a, 'name_ar': 'Synthetic A', 'country': 'test', 'tenant_key': uni_a}, {'id': uni_b, 'name_ar': 'Synthetic B', 'country': 'test', 'tenant_key': uni_b}]
            response = await db.post(url + '/rest/v1/universities', headers=header, json=universities)
            assert response.status_code == 201, (response.status_code, response.text)
            mappings = [dict(owner_user_id=a[0], university_id=uni_a, university_student_id='123456789'), dict(owner_user_id=b[0], university_id=uni_b, university_student_id='123456789'), dict(owner_user_id=a2[0], university_id=uni_a, university_student_id='987654321')]
            response = await db.post(url + '/rest/v1/student_university_identities', headers=header, json=mappings)
            assert response.status_code == 201, (response.status_code, response.text)
            app = FastAPI(); app.include_router(router)
            app.state.auth_http_client = db
            app.state.university_event_store = UniversityEventStore(url, service, db)
            app.state.university_identity_repository = SupabaseUniversityIdentityRepository(url, service, db)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as api:
                async def send(payload, key):
                    body = json.dumps(payload, separators=(',', ':')).encode()
                    sig = 'sha256=' + hmac.new(key.encode(), body, hashlib.sha256).hexdigest()
                    return await api.post('/api/v1/uni/webhook', content=body, headers={'X-Uni-Signature': sig})
                async def notifications(token):
                    return await api.get('/api/v1/me/university-notifications', headers={'Authorization': f'Bearer {token}'})
                shared_id = str(uuid4())
                event = {'id': shared_id, 'type': 'registration.opened', 'version': 1, 'occurredAt': '2026-10-21T00:00:00Z', 'payload': {}, 'idempotencyKey': 'shared-key-' + shared_id}
                monkeypatch.setattr(settings, 'uni_university_id', uni_a)
                monkeypatch.setattr(settings, 'uni_webhook_secret', SecretStr('phase4d-test-a'))
                assert (await send(event, 'wrong-test-key')).status_code == 401
                assert (await send({**event, 'universityId': uni_b}, 'phase4d-test-a')).status_code == 422
                response = await send(event, 'phase4d-test-a'); assert response.status_code == 202 and response.json()['applied'], response.text
                assert (await send(event, 'phase4d-test-a')).json()['duplicate']
                private = {**event, 'id': str(uuid4()), 'type': 'grade.posted', 'studentId': '123456789', 'idempotencyKey': 'private-a-' + shared_id}
                response = await send(private, 'phase4d-test-a'); assert response.status_code == 202 and response.json()['applied'], response.text
                a_rows = (await notifications(a[1])).json(); assert len(a_rows) == 2
                assert len((await notifications(a2[1])).json()) == 1
                assert (await notifications(b[1])).status_code == 403
                assert (await notifications(missing[1])).status_code == 403
                assert (await api.get('/api/v1/me/university-notifications')).status_code == 401
                assert (await notifications('invalid-test-token')).status_code == 401
                monkeypatch.setattr(settings, 'uni_university_id', uni_b)
                monkeypatch.setattr(settings, 'uni_webhook_secret', SecretStr('phase4d-test-b'))
                assert (await send(event, 'phase4d-test-a')).status_code == 401
                response = await send(event, 'phase4d-test-b'); assert response.status_code == 202 and response.json()['applied'], response.text
                b_private = {**private, 'id': str(uuid4()), 'idempotencyKey': 'private-b-' + shared_id}
                response = await send(b_private, 'phase4d-test-b'); assert response.status_code == 202 and response.json()['applied'], response.text
                b_rows = (await notifications(b[1])).json()
                assert {row['event_id'] for row in b_rows} == {shared_id, b_private['id']}
                assert private['id'] not in {row['event_id'] for row in b_rows}
                assert (await notifications(a[1])).status_code == 403
                denied = await db.get(url + '/rest/v1/student_notifications', headers={'apikey': anon, 'Authorization': 'Bearer ' + b[1]})
                assert denied.status_code in (401, 403), denied.status_code
                # Real Auth + PostgREST on the streaming iterator; then revoke the mapping.
                class Request:
                    headers = {'authorization': 'Bearer ' + b[1]}
                    state = SimpleNamespace()
                    async def is_disconnected(self): return False
                req = Request(); req.app = app
                stream = await my_university_stream(CurrentUser(b[0]), req)
                iterator = stream.body_iterator
                assert await anext(iterator) == 'retry: 3000\n\n'
                frames = (await anext(iterator)).strip().split('\n\n')
                assert {json.loads(frame.removeprefix('data: '))['event_id'] for frame in frames} == {shared_id, b_private['id']}
                deleted = await db.delete(url + '/rest/v1/student_university_identities', params={'owner_user_id': 'eq.' + b[0], 'university_id': 'eq.' + uni_b}, headers=header)
                assert deleted.status_code == 204
                with pytest.raises(StopAsyncIteration): await anext(iterator)
                assert (await notifications(b[1])).status_code == 403
    asyncio.run(run())
