"""Immutable learning-material domain contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MaterialStorageProvider(str, Enum):
    LOCAL_PRIVATE = "local_private"
    SUPABASE_PRIVATE = "supabase_private"


@dataclass(frozen=True)
class AuthorizedLearningMaterial:
    material_id: str
    university_id: str
    study_plan_id: str
    course_id: str
    course_code: str
    course_name_ar: str | None
    course_name_en: str | None
    title_ar: str
    title_en: str | None
    description_ar: str | None
    description_en: str | None
    material_type: str
    chapter_number: str | None
    display_order: int
    file_name: str
    mime_type: str
    byte_size: int
    sha256: str
    storage_provider: MaterialStorageProvider
    storage_bucket: str | None
    object_key: str
    version_label: str


class LearningMaterialError(RuntimeError):
    """Base error with no student-private details in its message."""


class LearningMaterialNotFound(LearningMaterialError):
    pass


class LearningMaterialIntegrityError(LearningMaterialError):
    pass


class LearningMaterialTransportError(LearningMaterialError):
    pass
