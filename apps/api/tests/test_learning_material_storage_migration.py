from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import pytest

from apps.api.scripts import migrate_learning_materials_to_storage as migration


PAYLOAD = b"private chapter bytes"
REAL_HTTPX_CLIENT = httpx.Client
ROW = {
    "id": "material-1",
    "object_key": "zu/ai-p12/1505311/lecture-01.pdf",
    "mime_type": "application/pdf",
    "byte_size": len(PAYLOAD),
    "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
    "storage_provider": "local_private",
    "storage_bucket": None,
}


def _bucket() -> dict:
    return {
        "public": False,
        "file_size_limit": migration.EXPECTED_FILE_SIZE_LIMIT,
        "allowed_mime_types": sorted(migration.EXPECTED_MIME_TYPES),
    }


def _install_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(migration, "ROOT", tmp_path)
    source = tmp_path / ROW["object_key"]
    source.parent.mkdir(parents=True)
    source.write_bytes(PAYLOAD)


def test_hosted_target_requires_explicit_gate() -> None:
    with pytest.raises(RuntimeError, match="refusing hosted Supabase"):
        migration.migrate("https://example.supabase.co", "secret", apply=False, allow_hosted=False)


def test_dry_run_only_reads_and_verifies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_source(monkeypatch, tmp_path)
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.url.path.endswith("/storage/v1/bucket/learning-materials"):
            return httpx.Response(200, json=_bucket())
        if request.url.path.endswith("/rest/v1/learning_materials"):
            return httpx.Response(200, json=[ROW])
        raise AssertionError(request.url)

    monkeypatch.setattr(
        migration.httpx,
        "Client",
        lambda **kwargs: REAL_HTTPX_CLIENT(transport=httpx.MockTransport(handler), **kwargs),
    )
    assert migration.migrate("http://127.0.0.1:54321", "local-key", apply=False, allow_hosted=False) == 0
    assert methods == ["GET", "GET"]


def test_apply_verifies_upload_and_uses_optimistic_metadata_switch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_source(monkeypatch, tmp_path)
    patch_query = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal patch_query
        path = request.url.path
        if path.endswith("/storage/v1/bucket/learning-materials"):
            return httpx.Response(200, json=_bucket())
        if path.endswith("/rest/v1/learning_materials") and request.method == "GET":
            return httpx.Response(200, json=[ROW])
        if "/storage/v1/object/learning-materials/" in path and request.method == "POST":
            assert request.headers["x-upsert"] == "true"
            assert request.content == PAYLOAD
            return httpx.Response(200, json={"Key": ROW["object_key"]})
        if "/storage/v1/object/authenticated/learning-materials/" in path:
            return httpx.Response(200, content=PAYLOAD)
        if path.endswith("/rest/v1/learning_materials") and request.method == "PATCH":
            patch_query = request.url.query.decode()
            assert request.headers["prefer"] == "return=representation"
            return httpx.Response(200, json=[{"id": ROW["id"]}])
        raise AssertionError(request.url)

    monkeypatch.setattr(
        migration.httpx,
        "Client",
        lambda **kwargs: REAL_HTTPX_CLIENT(transport=httpx.MockTransport(handler), **kwargs),
    )
    assert migration.migrate("http://localhost:54321", "local-key", apply=True, allow_hosted=False) == 0
    assert "storage_provider=eq.local_private" in patch_query
    assert "sha256=eq." in patch_query
    assert "byte_size=eq." in patch_query
    assert "object_key=eq." in patch_query


def test_apply_rerun_verifies_already_migrated_object_without_writes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _install_source(monkeypatch, tmp_path)
    migrated_row = {**ROW, "storage_provider": "supabase_private", "storage_bucket": migration.BUCKET}
    writes: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method in {"POST", "PATCH", "DELETE"}:
            writes.append(request.method)
        path = request.url.path
        if path.endswith("/storage/v1/bucket/learning-materials"):
            return httpx.Response(200, json=_bucket())
        if path.endswith("/rest/v1/learning_materials"):
            return httpx.Response(200, json=[migrated_row])
        if "/storage/v1/object/authenticated/learning-materials/" in path:
            return httpx.Response(200, content=PAYLOAD)
        raise AssertionError(request.url)

    monkeypatch.setattr(
        migration.httpx,
        "Client",
        lambda **kwargs: REAL_HTTPX_CLIENT(transport=httpx.MockTransport(handler), **kwargs),
    )
    assert migration.migrate("http://localhost:54321", "local-key", apply=True, allow_hosted=False) == 0
    assert writes == []


def test_bucket_restrictions_are_required() -> None:
    with pytest.raises(RuntimeError, match="file-size limit"):
        migration._validate_bucket({**_bucket(), "file_size_limit": None})
