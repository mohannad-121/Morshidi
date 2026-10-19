from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.main import app

USER = "10000000-0000-0000-0000-000000000001"


class RegistrationStub:
    def __init__(self):
        self.calls = []

    async def context(self, owner):
        self.calls.append(("context", owner))
        return {"success": True, "context": {"planKey": "ZU:IT:CS:P12"}}

    async def offerings(self, owner):
        self.calls.append(("offerings", owner))
        return {"success": True, "offerings": []}

    async def preview(self, owner, ids):
        self.calls.append(("preview", owner, ids))
        return {"success": False, "preview": {"canRegister": False, "issues": [{"code": "SECTION_FULL"}]}}

    async def register(self, owner, ids, key):
        self.calls.append(("register", owner, ids, key))
        return {"success": True, "enrollments": []}

    async def drop(self, owner, section_id, key):
        self.calls.append(("drop", owner, section_id, key))
        return {"success": True, "enrollments": []}


def test_registration_routes_bind_owner_and_preserve_authoritative_preview():
    stub = RegistrationStub()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(USER)
    previous = getattr(app.state, "registration_service", None)
    try:
        with TestClient(app) as client:
            app.state.registration_service = stub
            context = client.get("/api/v1/me/registration/context")
            assert context.status_code == 200
            assert context.json()["context"]["planKey"] == "ZU:IT:CS:P12"
            preview = client.post("/api/v1/me/registration/preview", json={"section_ids": ["SEC-1"]})
            assert preview.status_code == 200
            assert preview.json()["preview"]["issues"][0]["code"] == "SECTION_FULL"
            registered = client.post("/api/v1/me/registration/register", json={"section_ids": ["SEC-1"]},
                                     headers={"Idempotency-Key": "register-key"})
            assert registered.status_code == 200
            assert ("register", USER, ["SEC-1"], "register-key") in stub.calls
    finally:
        app.state.registration_service = previous
        app.dependency_overrides.clear()


def test_registration_mutations_require_idempotency_key():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(USER)
    previous = getattr(app.state, "registration_service", None)
    try:
        with TestClient(app) as client:
            app.state.registration_service = RegistrationStub()
            response = client.post("/api/v1/me/registration/register", json={"section_ids": ["SEC-1"]})
            assert response.status_code == 400
            assert response.json()["detail"] == "IDEMPOTENCY_KEY_REQUIRED"
    finally:
        app.state.registration_service = previous
        app.dependency_overrides.clear()
