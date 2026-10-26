import asyncio
from dataclasses import dataclass

import pytest

from app.registration.service import RegistrationService, RegistrationUnavailableError


@dataclass
class Identity:
    university_student_id: str = "209900003"


class IdentityRepo:
    def __init__(self, identity=Identity()):
        self.identity = identity
        self.calls = []

    async def get_university_identity_for_user(self, owner, university):
        self.calls.append((owner, university))
        return self.identity


class Client:
    def __init__(self):
        self.calls = []

    async def exchange_student_token(self, student_id):
        self.calls.append(("exchange", student_id))
        return "scoped-token"

    async def registration_request(self, method, path, token, *, payload=None, idempotency_key=None):
        self.calls.append((method, path, token, payload, idempotency_key))
        if path.endswith("/register") or path.endswith("/drop"):
            return {"success": True, "enrollments": []}
        if path.endswith("/offerings"):
            return {"success": True, "offerings": []}
        return {"success": True}

    async def source_manifest(self, token):
        self.calls.append(("manifest", token))
        return {"synthetic": True}


class Sync:
    def __init__(self):
        self.calls = []

    async def refresh_existing_student(self, owner, token):
        self.calls.append((owner, token))


def test_registration_uses_authenticated_owner_mapping_and_scoped_token():
    identities, client, sync = IdentityRepo(), Client(), Sync()
    service = RegistrationService(client, identities, "university-uuid", sync)
    asyncio.run(service.context("owner-uuid"))
    assert identities.calls == [("owner-uuid", "university-uuid")]
    assert client.calls[0] == ("exchange", "209900003")
    assert client.calls[1][1].endswith("/registration/context")
    assert "209900003" not in client.calls[1][1]


def test_register_and_drop_forward_idempotency_and_refresh_only_after_success():
    client, sync = Client(), Sync()
    service = RegistrationService(client, IdentityRepo(), "university-uuid", sync)
    asyncio.run(service.register("owner", ["SEC-1"], "register-key"))
    asyncio.run(service.drop("owner", "SEC-1", "drop-key"))
    mutation_calls = [call for call in client.calls if call[0] == "POST"]
    assert mutation_calls[0][3:] == ({"sectionIds": ["SEC-1"]}, "register-key")
    assert mutation_calls[1][3:] == ({"sectionId": "SEC-1"}, "drop-key")
    assert sync.calls == [("owner", "scoped-token"), ("owner", "scoped-token")]


def test_missing_owner_mapping_fails_before_upstream_call():
    client = Client()
    service = RegistrationService(client, IdentityRepo(None), "university-uuid")
    with pytest.raises(RegistrationUnavailableError, match="UNIVERSITY_IDENTITY_NOT_LINKED"):
        asyncio.run(service.offerings("unknown-owner"))
    assert client.calls == []


def test_offering_source_reuses_one_owner_scoped_token_for_read_only_calls():
    identities, client = IdentityRepo(), Client()
    service = RegistrationService(client, identities, "university-uuid")

    context, offerings, manifest = asyncio.run(service.offering_source("owner-uuid"))

    assert context["success"] is True
    assert offerings == []
    assert manifest == {"synthetic": True}
    assert [call for call in client.calls if call[0] == "exchange"] == [
        ("exchange", "209900003")
    ]
    assert {call[1] for call in client.calls if call[0] == "GET"} == {
        "/api/integrations/morshidi/v1/student/registration/context",
        "/api/integrations/morshidi/v1/student/registration/offerings",
    }
