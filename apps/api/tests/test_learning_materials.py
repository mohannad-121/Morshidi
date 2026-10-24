from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest

from app.learning_materials.models import (
    AuthorizedLearningMaterial,
    LearningMaterialIntegrityError,
    LearningMaterialNotFound,
    MaterialStorageProvider,
)
from app.learning_materials.repository import SupabaseLearningMaterialRepository
from app.learning_materials.service import LearningMaterialService


UNIVERSITY_A = "10000000-0000-0000-0000-000000000001"
UNIVERSITY_B = "20000000-0000-0000-0000-000000000001"
AI_PLAN = "10000000-0000-0000-0000-000000000005"
NURSING_PLAN = "2a78bbbb-0dc0-5c46-8630-7a46e4179830"
COURSE_ID = "30000000-0000-0000-0000-000000000001"
MATERIAL_ID = "40000000-0000-0000-0000-000000000001"


def _material(**changes) -> AuthorizedLearningMaterial:
    item = AuthorizedLearningMaterial(
        material_id=MATERIAL_ID,
        university_id=UNIVERSITY_A,
        study_plan_id=AI_PLAN,
        course_id=COURSE_ID,
        course_code="1505311",
        course_name_ar="تعلم الالة",
        course_name_en="Machine Learning",
        title_ar="المحاضرة 1",
        title_en="Lecture 1",
        description_ar=None,
        description_en=None,
        material_type="lecture",
        chapter_number="1",
        display_order=1,
        file_name="lecture-01.pdf",
        mime_type="application/pdf",
        byte_size=3,
        sha256="ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        storage_provider=MaterialStorageProvider.LOCAL_PRIVATE,
        storage_bucket=None,
        object_key="zu/ai-p12/1505311/lecture-01.pdf",
        version_label="legacy-v1",
    )
    return replace(item, **changes)


class FakeStudents:
    def __init__(self, plan: str = AI_PLAN, university: str = UNIVERSITY_A) -> None:
        self.plan = plan
        self.university = university

    async def get_profile(self, owner: str):
        return SimpleNamespace(study_plan_id=self.plan)

    async def resolve_student_university_id(self, owner: str) -> str:
        return self.university


class FakeRepository:
    def __init__(self, rows_by_scope=None) -> None:
        self.rows_by_scope = rows_by_scope or {}
        self.calls = []

    async def list_authorized(self, *, university_id, study_plan_id, material_id=None):
        self.calls.append((university_id, study_plan_id, material_id))
        rows = self.rows_by_scope.get((university_id, study_plan_id), ())
        return tuple(row for row in rows if material_id is None or row.material_id == material_id)


@pytest.mark.anyio
async def test_ai_student_sees_only_explicit_ai_authorization(tmp_path: Path):
    repository = FakeRepository({(UNIVERSITY_A, AI_PLAN): (_material(),)})
    service = LearningMaterialService(repository, FakeStudents(), tmp_path)
    assert await service.list_for_owner("owner") == (_material(),)
    assert repository.calls == [(UNIVERSITY_A, AI_PLAN, None)]


@pytest.mark.anyio
async def test_nursing_student_gets_accurate_empty_library(tmp_path: Path):
    service = LearningMaterialService(FakeRepository(), FakeStudents(NURSING_PLAN), tmp_path)
    assert await service.list_for_owner("owner") == ()


@pytest.mark.anyio
async def test_shared_course_does_not_share_material_without_explicit_plan_authorization(tmp_path: Path):
    shared_course = _material(course_code="1501112")
    repository = FakeRepository({(UNIVERSITY_A, AI_PLAN): (shared_course,)})
    nursing = LearningMaterialService(repository, FakeStudents(NURSING_PLAN), tmp_path)
    assert await nursing.list_for_owner("owner") == ()


@pytest.mark.anyio
async def test_shared_course_is_visible_after_explicit_second_plan_authorization(tmp_path: Path):
    shared_course = _material(course_code="1501112", study_plan_id=NURSING_PLAN)
    repository = FakeRepository({(UNIVERSITY_A, NURSING_PLAN): (shared_course,)})
    nursing = LearningMaterialService(repository, FakeStudents(NURSING_PLAN), tmp_path)
    assert await nursing.list_for_owner("owner") == (shared_course,)


@pytest.mark.anyio
async def test_unknown_curriculum_has_no_implicit_fallback(tmp_path: Path):
    unknown_plan = "90000000-0000-0000-0000-000000000001"
    service = LearningMaterialService(FakeRepository(), FakeStudents(unknown_plan), tmp_path)
    assert await service.list_for_owner("owner") == ()


@pytest.mark.anyio
async def test_overlapping_course_code_is_tenant_scoped(tmp_path: Path):
    tenant_b_material = _material(
        material_id="40000000-0000-0000-0000-000000000002",
        university_id=UNIVERSITY_B,
        title_en="Different institutional content",
    )
    repository = FakeRepository({
        (UNIVERSITY_A, AI_PLAN): (_material(),),
        (UNIVERSITY_B, AI_PLAN): (tenant_b_material,),
    })
    service = LearningMaterialService(repository, FakeStudents(AI_PLAN, UNIVERSITY_B), tmp_path)
    assert await service.list_for_owner("owner") == (tenant_b_material,)


@pytest.mark.anyio
async def test_plan_switch_re_resolves_authorization_scope(tmp_path: Path):
    students = FakeStudents(AI_PLAN)
    repository = FakeRepository({(UNIVERSITY_A, AI_PLAN): (_material(),)})
    service = LearningMaterialService(repository, students, tmp_path)
    assert len(await service.list_for_owner("owner")) == 1
    students.plan = NURSING_PLAN
    assert await service.list_for_owner("owner") == ()


@pytest.mark.anyio
async def test_direct_unauthorized_material_access_is_not_found(tmp_path: Path):
    service = LearningMaterialService(FakeRepository(), FakeStudents(NURSING_PLAN), tmp_path)
    with pytest.raises(LearningMaterialNotFound):
        await service.get_for_owner("owner", UUID(MATERIAL_ID))


def test_private_local_path_rejects_traversal(tmp_path: Path):
    service = LearningMaterialService(FakeRepository(), FakeStudents(), tmp_path)
    with pytest.raises(LearningMaterialIntegrityError):
        service.verified_local_path(_material(object_key="../public/secret.pdf"))


def test_private_local_path_verifies_size_and_sha256(tmp_path: Path):
    path = tmp_path / "zu/ai-p12/1505311/lecture-01.pdf"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"abc")
    service = LearningMaterialService(FakeRepository(), FakeStudents(), tmp_path)
    assert service.verified_local_path(_material()) == path.resolve()
    path.write_bytes(b"abd")
    with pytest.raises(LearningMaterialIntegrityError):
        service.verified_local_path(_material())


@pytest.mark.anyio
async def test_repository_rejects_malformed_material_metadata():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/learning_material_authorizations"):
            return httpx.Response(200, json=[{
                "material_id": MATERIAL_ID,
                "course_id": COURSE_ID,
                "authorization_status": "published",
                "valid_from": None,
                "valid_to": None,
            }])
        return httpx.Response(200, json=[{
            "id": MATERIAL_ID,
            "university_id": UNIVERSITY_A,
            "course_id": COURSE_ID,
            "title_ar": "المحاضرة 1",
            "title_en": None,
            "description_ar": None,
            "description_en": None,
            "material_type": "lecture",
            "chapter_number": 1,
            "display_order": "not-an-integer",
            "file_name": "lecture.pdf",
            "mime_type": "application/pdf",
            "byte_size": 3,
            "sha256": "a" * 64,
            "storage_provider": "local_private",
            "storage_bucket": None,
            "object_key": "safe/lecture.pdf",
            "version_label": "v1",
            "publication_status": "published",
            "courses": {"course_code": "1505311", "name_ar": "تعلم الالة", "name_en": None},
        }])

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        repository = SupabaseLearningMaterialRepository("https://example.supabase.co", "test-key", client)
        with pytest.raises(LearningMaterialIntegrityError):
            await repository.list_authorized(university_id=UNIVERSITY_A, study_plan_id=AI_PLAN)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("signed_path", "expected"),
    (
        ("/object/sign/private/path.pdf?token=local", "https://example.supabase.co/storage/v1/object/sign/private/path.pdf?token=local"),
        ("/storage/v1/object/sign/private/path.pdf?token=local", "https://example.supabase.co/storage/v1/object/sign/private/path.pdf?token=local"),
    ),
)
async def test_repository_normalizes_supported_private_storage_signed_paths(signed_path, expected):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"signedURL": signed_path})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        repository = SupabaseLearningMaterialRepository("https://example.supabase.co", "test-key", client)
        assert await repository.create_signed_url(bucket="private", object_key="path.pdf") == expected


def test_migration_has_fail_closed_scope_and_no_public_chapter_binaries():
    root = Path(__file__).resolve().parents[3]
    migration = (root / "supabase/migrations/20261022135845_add_learning_material_authorization.sql").read_text("utf-8")
    assert "foreign key (study_plan_id, course_id)" in migration
    assert "profile.owner_user_id = (select auth.uid())" in migration
    assert "material_auth.authorization_status = 'published'" in migration
    assert "USER_CONFIRMED_AI_PLAN_12_LEGACY_UPLOAD_2026-10-22" in migration
    assert not list((root / "apps/web/public/chapters").glob("**/*.pdf"))
    assert not list((root / "apps/web/public/chapters").glob("**/*.pptx"))
