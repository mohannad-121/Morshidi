import asyncio
import hashlib
import hmac
import json
from types import SimpleNamespace
from uuid import uuid4
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.main import app, lifespan
from app.university_sync.event_routes import my_university_stream, router
from app.university_sync.events import UniversityEventStore
import app.university_sync.event_routes as event_routes

UNI = '22222222-2222-2222-2222-222222222222'
def enable_stream_auth(monkeypatch):
    async def current(request, credentials):
        assert credentials.credentials == 'test-token'
        return CurrentUser('a')
    monkeypatch.setattr(event_routes, 'get_current_user', current)
class Identities:
    async def get_university_identity_for_user(self, owner, university):
        assert university == UNI
        return SimpleNamespace(owner_user_id=owner, university_id=university, university_student_id={'a': '123456789', 'b': '987654321'}.get(owner, ''))
class Store:
    def __init__(self): self.events = []
    async def ingest(self, university, event):
        assert university == UNI
        if any(item['id'] == event['id'] or item['idempotencyKey'] == event['idempotencyKey'] for item in self.events):
            return {'duplicate': True, 'applied': False}
        self.events.append(event)
        return {'duplicate': False, 'applied': True}
    async def list_notifications(self, university, student, since=None, *, after_id=None):
        assert university == UNI
        rows = [dict(id=1, summary='global', student_id=None, created_at='2026-01-01T00:00:00Z'), dict(id=2, summary='private', student_id='123456789', created_at='2026-01-02T00:00:00Z')]
        return [row for row in rows if row['student_id'] in (None, student) and (since is None or row['created_at'] > since) and (after_id is None or row['id'] > after_id)]
@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, 'uni_university_id', UNI)
    monkeypatch.setattr(settings, 'uni_webhook_secret', SecretStr('test-key'))
    api = FastAPI(); api.include_router(router)
    api.state.university_event_store = Store(); api.state.university_identity_repository = Identities()
    async def current(): return CurrentUser('a')
    api.dependency_overrides[get_current_user] = current
    with TestClient(api) as c: yield c, api

def event(kind='registration.opened', student=None):
    return {'id': str(uuid4()), 'type': kind, 'version': 1, 'occurredAt': '2026-01-01T00:00:00Z', 'studentId': student, 'payload': {}, 'idempotencyKey': str(uuid4())}
def post(c, value, key=b'test-key'):
    body = json.dumps(value).encode()
    sig = 'sha256=' + hmac.new(key, body, hashlib.sha256).hexdigest()
    return c.post('/api/v1/uni/webhook', content=body, headers={'X-Uni-Signature': sig})
def test_registered_once():
    for method, path in [('POST', '/api/v1/uni/webhook'), ('GET', '/api/v1/me/university-notifications'), ('GET', '/api/v1/me/university-stream')]:
        routes = [route for included in app.routes for route in getattr(getattr(included, 'original_router', None), 'routes', [])]
        assert sum(getattr(r, 'path', None) == path and method in getattr(r, 'methods', set()) for r in routes) == 1
        assert method.lower() in app.openapi()['paths'][path]
def test_lifespan_uses_shared_client(monkeypatch):
    async def run():
        monkeypatch.setattr(settings, 'supabase_url', None); monkeypatch.setattr(settings, 'supabase_secret_key', None)
        instance = FastAPI()
        async with lifespan(instance): assert instance.state.university_event_store is None
        monkeypatch.setattr(settings, 'supabase_url', 'https://db.example'); monkeypatch.setattr(settings, 'supabase_secret_key', SecretStr('test-key'))
        instance = FastAPI()
        async with lifespan(instance):
            assert isinstance(instance.state.university_event_store, UniversityEventStore)
            assert instance.state.university_event_store._client is instance.state.auth_http_client
        assert instance.state.auth_http_client.is_closed
    asyncio.run(run())
def test_webhook_validation_and_replay(client):
    c, api = client; payload = event()
    assert post(c, payload, b'wrong').status_code == 401
    assert post(c, payload).json() == {'duplicate': False, 'applied': True}
    assert post(c, payload).json() == {'duplicate': True, 'applied': False}
    assert len(api.state.university_event_store.events) == 1
    assert post(c, event('grade.posted')).status_code == 422
    assert post(c, event('grade.posted', '123456789')).status_code == 202
    assert post(c, {**event(), 'type': 'unsupported'}).status_code == 422
    assert c.post('/api/v1/uni/webhook', content=b'x' * (128 * 1024 + 1)).status_code == 413
def test_student_scope(client):
    c, api = client
    assert [x['summary'] for x in c.get('/api/v1/me/university-notifications?studentId=987654321').json()] == ['global', 'private']
    async def other(): return CurrentUser('b')
    api.dependency_overrides[get_current_user] = other
    assert [x['summary'] for x in c.get('/api/v1/me/university-notifications').json()] == ['global']
    async def unlinked(): return CurrentUser('unlinked')
    api.dependency_overrides[get_current_user] = unlinked
    assert c.get('/api/v1/me/university-notifications').status_code == 403
    api.dependency_overrides.clear()
    assert c.get('/api/v1/me/university-notifications').status_code == 401
def test_sse_serialization_and_cursor(monkeypatch):
    monkeypatch.setattr(settings, 'uni_university_id', UNI)
    enable_stream_auth(monkeypatch)
    class Request:
        headers = {'authorization': 'Bearer test-token'}
        app = SimpleNamespace(state=SimpleNamespace(university_identity_repository=Identities(), university_event_store=Store()))
        async def is_disconnected(self): return False
    async def run():
        response = await my_university_stream(CurrentUser('a'), Request(), since='2026-01-01T00:00:00Z')
        iterator = response.body_iterator
        assert await anext(iterator) == 'retry: 3000\n\n'
        frame = await anext(iterator)
        assert json.loads(frame.removeprefix('data: ').strip())['summary'] == 'private'
        await iterator.aclose()
    asyncio.run(run())

def test_missing_configuration_returns_controlled_errors(client, monkeypatch):
    c, api = client
    monkeypatch.setattr(settings, 'uni_webhook_secret', None)
    assert post(c, event()).status_code == 503
    monkeypatch.setattr(settings, 'uni_university_id', None)
    assert c.get('/api/v1/me/university-notifications').status_code == 503
    monkeypatch.setattr(settings, 'uni_university_id', UNI)
    api.state.university_event_store = None
    assert c.get('/api/v1/me/university-notifications').status_code == 503

def test_stream_store_error_and_disconnect(monkeypatch):
    monkeypatch.setattr(settings, 'uni_university_id', UNI)
    enable_stream_auth(monkeypatch)
    class Broken:
        async def list_notifications(self, *args, **kwargs): raise RuntimeError('private details')
    class Request:
        headers = {'authorization': 'Bearer test-token'}
        app = SimpleNamespace(state=SimpleNamespace(university_identity_repository=Identities(), university_event_store=Broken()))
        async def is_disconnected(self): return False
    async def run():
        response = await my_university_stream(CurrentUser('a'), Request())
        iterator = response.body_iterator
        await anext(iterator)
        frame = await anext(iterator)
        assert frame == 'event: sync-error\ndata: {}\n\n'
        assert 'private details' not in frame
        await iterator.aclose()
        class Disconnected(Request):
            async def is_disconnected(self): return True
        response = await my_university_stream(CurrentUser('a'), Disconnected())
        iterator = response.body_iterator
        await anext(iterator)
        with pytest.raises(StopAsyncIteration): await anext(iterator)
    asyncio.run(run())

def test_invalid_identity_and_configuration_fail_closed(client, monkeypatch):
    c, api = client
    class WrongIdentity:
        async def get_university_identity_for_user(self, owner, university):
            return SimpleNamespace(owner_user_id=owner, university_id='33333333-3333-3333-3333-333333333333', university_student_id='123456789')
    api.state.university_identity_repository = WrongIdentity()
    assert c.get('/api/v1/me/university-notifications').status_code == 403
    assert c.get('/api/v1/me/university-stream').status_code == 403
    monkeypatch.setattr(settings, 'uni_university_id', 'invalid')
    assert c.get('/api/v1/me/university-notifications').status_code == 503
    assert post(c, event()).status_code == 503


def test_poll_and_stream_apply_same_university_and_student_scope(client, monkeypatch):
    c, api = client
    enable_stream_auth(monkeypatch)
    other = '33333333-3333-3333-3333-333333333333'
    class ScopedStore:
        rows = [
            {'id': 1, 'university': UNI, 'student_id': None, 'summary': 'A broadcast'},
            {'id': 2, 'university': other, 'student_id': None, 'summary': 'B broadcast'},
            {'id': 3, 'university': UNI, 'student_id': '123456789', 'summary': 'A private'},
            {'id': 4, 'university': other, 'student_id': '123456789', 'summary': 'B same student'},
            {'id': 5, 'university': UNI, 'student_id': '987654321', 'summary': 'other student'},
        ]
        async def list_notifications(self, university, student, since=None, *, after_id=None):
            return [r for r in self.rows if r['university'] == university and r['student_id'] in (None, student)]
    api.state.university_event_store = ScopedStore()
    assert [r['summary'] for r in c.get('/api/v1/me/university-notifications').json()] == ['A broadcast', 'A private']
    class Request:
        headers = {'authorization': 'Bearer test-token'}
        app = api
        async def is_disconnected(self): return False
    async def run():
        response = await my_university_stream(CurrentUser('a'), Request())
        iterator = response.body_iterator
        await anext(iterator)
        frames = (await anext(iterator)).strip().split('\n\n')
        await iterator.aclose()
        return [json.loads(frame.removeprefix('data: ').strip())['summary'] for frame in frames]
    assert asyncio.run(run()) == ['A broadcast', 'A private']
    class OtherIdentities:
        async def get_university_identity_for_user(self, owner, university):
            return SimpleNamespace(owner_user_id=owner, university_id=university, university_student_id='123456789')
    api.state.university_identity_repository = OtherIdentities()
    monkeypatch.setattr(settings, 'uni_university_id', other)
    assert [r['summary'] for r in c.get('/api/v1/me/university-notifications').json()] == ['B broadcast', 'B same student']
    assert asyncio.run(run()) == ['B broadcast', 'B same student']

@pytest.mark.parametrize('change', ['revoked', 'moved', 'changed_student', 'auth_invalid'])
def test_stream_stops_before_next_poll_after_authorization_changes(monkeypatch, change):
    monkeypatch.setattr(settings, 'uni_university_id', UNI)
    state = {'valid': True, 'calls': 0}
    class Identity:
        async def get_university_identity_for_user(self, owner, university):
            if not state['valid']:
                if change == 'revoked': return None
                if change == 'moved': return SimpleNamespace(owner_user_id='a', university_id='33333333-3333-3333-3333-333333333333', university_student_id='123456789')
                if change == 'changed_student': return SimpleNamespace(owner_user_id='a', university_id=UNI, university_student_id='987654321')
            return SimpleNamespace(owner_user_id='a', university_id=UNI, university_student_id='123456789')
    class CountingStore:
        async def list_notifications(self, *args, **kwargs):
            state['calls'] += 1
            return [{'id': 1, 'summary': 'allowed'}]
    class Request:
        headers = {'authorization': 'Bearer test-token'}
        app = SimpleNamespace(state=SimpleNamespace(university_identity_repository=Identity(), university_event_store=CountingStore()))
        async def is_disconnected(self): return False
    async def authenticate(request, credentials):
        if not state['valid'] and change == 'auth_invalid':
            from fastapi import HTTPException
            raise HTTPException(401)
        return CurrentUser('a')
    async def no_wait(_): pass
    monkeypatch.setattr(event_routes, 'get_current_user', authenticate)
    monkeypatch.setattr(event_routes.asyncio, 'sleep', no_wait)
    async def run():
        response = await my_university_stream(CurrentUser('a'), Request())
        iterator = response.body_iterator
        assert await anext(iterator) == 'retry: 3000\n\n'
        assert 'allowed' in await anext(iterator)
        state['valid'] = False
        with pytest.raises(StopAsyncIteration): await anext(iterator)
        assert state['calls'] == 1
    asyncio.run(run())
