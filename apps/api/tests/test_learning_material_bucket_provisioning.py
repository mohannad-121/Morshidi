from __future__ import annotations

import httpx
import pytest

from apps.api.scripts import provision_learning_material_bucket as provisioning


REAL_HTTPX_CLIENT = httpx.Client


def _bucket(**changes) -> dict:
    bucket = {
        "id": provisioning.BUCKET,
        "name": provisioning.BUCKET,
        "public": False,
        "file_size_limit": provisioning.EXPECTED_FILE_SIZE_LIMIT,
        "allowed_mime_types": sorted(provisioning.EXPECTED_MIME_TYPES),
    }
    return {**bucket, **changes}


def _install(monkeypatch: pytest.MonkeyPatch, handler) -> None:
    monkeypatch.setattr(
        provisioning.httpx,
        "Client",
        lambda **kwargs: REAL_HTTPX_CLIENT(transport=httpx.MockTransport(handler), **kwargs),
    )


def test_hosted_target_requires_explicit_gate() -> None:
    with pytest.raises(RuntimeError, match="refusing hosted Supabase"):
        provisioning.provision("https://example.supabase.co", "secret", apply=False, allow_hosted=False)


def test_dry_run_reports_missing_without_creation(monkeypatch: pytest.MonkeyPatch) -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        return httpx.Response(404)

    _install(monkeypatch, handler)
    assert provisioning.provision("http://127.0.0.1:54321", "key", apply=False, allow_hosted=False) == 0
    assert methods == ["GET"]


def test_local_storage_api_missing_bucket_shape_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": "NoSuchBucket", "message": "Bucket not found"})

    _install(monkeypatch, handler)
    assert provisioning.provision("http://localhost:54321", "key", apply=False, allow_hosted=False) == 0


def test_apply_creates_and_revalidates_exact_private_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if methods == ["GET"]:
            return httpx.Response(404)
        if request.method == "POST":
            payload = __import__("json").loads(request.content)
            assert payload == {
                "id": provisioning.BUCKET,
                "name": provisioning.BUCKET,
                "public": False,
                "file_size_limit": provisioning.EXPECTED_FILE_SIZE_LIMIT,
                "allowed_mime_types": sorted(provisioning.EXPECTED_MIME_TYPES),
            }
            return httpx.Response(200, json={"name": provisioning.BUCKET})
        return httpx.Response(200, json=_bucket())

    _install(monkeypatch, handler)
    assert provisioning.provision("http://localhost:54321", "key", apply=True, allow_hosted=False) == 0
    assert methods == ["GET", "POST", "GET"]


def test_existing_compatible_bucket_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        return httpx.Response(200, json=_bucket())

    _install(monkeypatch, handler)
    assert provisioning.provision("http://localhost:54321", "key", apply=True, allow_hosted=False) == 0
    assert methods == ["GET"]


def test_existing_incompatible_bucket_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, lambda request: httpx.Response(200, json=_bucket(public=True)))
    with pytest.raises(RuntimeError, match="not private"):
        provisioning.provision("http://localhost:54321", "key", apply=True, allow_hosted=False)


def test_creation_race_revalidates_compatible_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(404)
        if calls == 2:
            return httpx.Response(409)
        return httpx.Response(200, json=_bucket())

    _install(monkeypatch, handler)
    assert provisioning.provision("http://localhost:54321", "key", apply=True, allow_hosted=False) == 0
