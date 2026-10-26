"""Authenticated-owner orchestration for learning materials."""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID

from app.services.student import StudentService

from .models import (
    AuthorizedLearningMaterial,
    LearningMaterialIntegrityError,
    LearningMaterialNotFound,
    MaterialStorageProvider,
)
from .repository import SupabaseLearningMaterialRepository


class LearningMaterialService:
    def __init__(
        self,
        repository: SupabaseLearningMaterialRepository,
        students: StudentService,
        private_root: Path,
    ) -> None:
        self._repository = repository
        self._students = students
        self._private_root = private_root.resolve()

    async def list_for_owner(self, owner: str) -> tuple[AuthorizedLearningMaterial, ...]:
        profile = await self._students.get_profile(owner)
        university_id = await self._students.resolve_student_university_id(owner)
        return await self._repository.list_authorized(
            university_id=university_id,
            study_plan_id=profile.study_plan_id,
        )

    async def get_for_owner(self, owner: str, material_id: UUID | str) -> AuthorizedLearningMaterial:
        profile = await self._students.get_profile(owner)
        university_id = await self._students.resolve_student_university_id(owner)
        materials = await self._repository.list_authorized(
            university_id=university_id,
            study_plan_id=profile.study_plan_id,
            material_id=str(material_id),
        )
        if len(materials) != 1:
            raise LearningMaterialNotFound("Learning material is unavailable")
        return materials[0]

    def verified_local_path(self, material: AuthorizedLearningMaterial) -> Path:
        if material.storage_provider is not MaterialStorageProvider.LOCAL_PRIVATE:
            raise LearningMaterialIntegrityError("Material is not locally stored")
        candidate = (self._private_root / material.object_key).resolve()
        try:
            candidate.relative_to(self._private_root)
        except ValueError as error:
            raise LearningMaterialIntegrityError("Material path escapes the private root") from error
        if not candidate.is_file() or candidate.stat().st_size != material.byte_size:
            raise LearningMaterialIntegrityError("Private material file is missing or has changed")
        hasher = hashlib.sha256()
        with candidate.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        if digest != material.sha256:
            raise LearningMaterialIntegrityError("Private material checksum mismatch")
        return candidate

    async def signed_storage_url(self, material: AuthorizedLearningMaterial) -> str:
        if material.storage_provider is not MaterialStorageProvider.SUPABASE_PRIVATE:
            raise LearningMaterialIntegrityError("Material is not stored in private object storage")
        if material.storage_bucket is None:
            raise LearningMaterialIntegrityError("Material is missing its private bucket")
        return await self._repository.create_signed_url(
            bucket=material.storage_bucket,
            object_key=material.object_key,
        )
