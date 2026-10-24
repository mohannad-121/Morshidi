"""Server-side persistence adapter for scoped learning materials."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping
from urllib.parse import quote
from uuid import UUID

import httpx

from .models import (
    AuthorizedLearningMaterial,
    LearningMaterialIntegrityError,
    LearningMaterialTransportError,
    MaterialStorageProvider,
)


class SupabaseLearningMaterialRepository:
    def __init__(self, supabase_url: str, server_key: str, client: httpx.AsyncClient) -> None:
        self._base_url = supabase_url.rstrip("/")
        self._rest_url = f"{self._base_url}/rest/v1"
        self._server_key = server_key
        self._client = client

    async def list_authorized(
        self,
        *,
        university_id: str,
        study_plan_id: str,
        material_id: str | None = None,
    ) -> tuple[AuthorizedLearningMaterial, ...]:
        university_id = str(UUID(university_id))
        study_plan_id = str(UUID(study_plan_id))
        if material_id is not None:
            material_id = str(UUID(material_id))

        authorization_params = {
            "select": "material_id,course_id,authorization_status,valid_from,valid_to",
            "university_id": f"eq.{university_id}",
            "study_plan_id": f"eq.{study_plan_id}",
            "authorization_status": "eq.published",
            "limit": "1000",
        }
        if material_id is not None:
            authorization_params["material_id"] = f"eq.{material_id}"
        authorization_rows = await self._get_rows(
            "learning_material_authorizations", authorization_params
        )
        today = date.today()
        active = tuple(row for row in authorization_rows if _active_on(row, today))
        if not active:
            return ()

        authorization_by_material: dict[str, str] = {}
        for row in active:
            found_material_id = _uuid_text(row, "material_id", "authorization")
            found_course_id = _uuid_text(row, "course_id", "authorization")
            existing = authorization_by_material.get(found_material_id)
            if existing is not None and existing != found_course_id:
                raise LearningMaterialIntegrityError("Conflicting material authorization scope")
            authorization_by_material[found_material_id] = found_course_id

        identifiers = ",".join(sorted(authorization_by_material))
        rows = await self._get_rows(
            "learning_materials",
            {
                "select": (
                    "id,university_id,course_id,title_ar,title_en,description_ar,description_en,"
                    "material_type,chapter_number,display_order,file_name,mime_type,byte_size,sha256,"
                    "storage_provider,storage_bucket,object_key,version_label,publication_status,"
                    "courses!inner(course_code,name_ar,name_en)"
                ),
                "id": f"in.({identifiers})",
                "university_id": f"eq.{university_id}",
                "publication_status": "eq.published",
                "limit": "1000",
            },
        )
        materials = tuple(
            _material(row, study_plan_id, authorization_by_material) for row in rows
        )
        if {item.material_id for item in materials} != set(authorization_by_material):
            raise LearningMaterialIntegrityError("Authorized material metadata is incomplete")
        return tuple(sorted(
            materials,
            key=lambda item: (
                item.course_name_ar or item.course_name_en or item.course_code,
                item.display_order,
                item.material_id,
            ),
        ))

    async def create_signed_url(
        self, *, bucket: str, object_key: str, expires_in: int = 120
    ) -> str:
        if not bucket or not object_key or expires_in < 1 or expires_in > 300:
            raise LearningMaterialIntegrityError("Invalid private storage request")
        path = f"{quote(bucket, safe='')}/{quote(object_key, safe='/')}"
        response = await self._client.post(
            f"{self._base_url}/storage/v1/object/sign/{path}",
            headers=self._headers(),
            json={"expiresIn": expires_in},
        )
        if not 200 <= response.status_code < 300:
            raise LearningMaterialTransportError("Private material signing failed")
        try:
            body = response.json()
        except ValueError as error:
            raise LearningMaterialTransportError("Private material signing failed") from error
        signed = body.get("signedURL") if isinstance(body, Mapping) else None
        if not isinstance(signed, str):
            raise LearningMaterialIntegrityError("Private storage returned an invalid signed path")
        if signed.startswith("/object/"):
            return f"{self._base_url}/storage/v1{signed}"
        if signed.startswith("/storage/v1/object/"):
            return f"{self._base_url}{signed}"
        raise LearningMaterialIntegrityError("Private storage returned an invalid signed path")

    async def _get_rows(self, resource: str, params: Mapping[str, str]) -> list[Mapping[str, Any]]:
        try:
            response = await self._client.get(
                f"{self._rest_url}/{resource}", params=params, headers=self._headers()
            )
        except (httpx.TimeoutException, httpx.RequestError) as error:
            raise LearningMaterialTransportError("Learning material storage unavailable") from error
        if not 200 <= response.status_code < 300:
            raise LearningMaterialTransportError("Learning material storage unavailable")
        try:
            body = response.json()
        except ValueError as error:
            raise LearningMaterialTransportError("Learning material storage returned invalid data") from error
        if not isinstance(body, list) or not all(isinstance(row, Mapping) for row in body):
            raise LearningMaterialIntegrityError("Learning material response is not a row array")
        return list(body)

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self._server_key,
            "Authorization": f"Bearer {self._server_key}",
            "Accept": "application/json",
        }


def _active_on(row: Mapping[str, Any], today: date) -> bool:
    def parse(value: Any) -> date | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise LearningMaterialIntegrityError("Authorization contains an invalid effective date")
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise LearningMaterialIntegrityError("Authorization contains an invalid effective date") from error

    starts, ends = parse(row.get("valid_from")), parse(row.get("valid_to"))
    return (starts is None or starts <= today) and (ends is None or ends >= today)


def _material(
    row: Mapping[str, Any],
    study_plan_id: str,
    authorization_by_material: Mapping[str, str],
) -> AuthorizedLearningMaterial:
    material_id = _uuid_text(row, "id", "material")
    university_id = _uuid_text(row, "university_id", "material")
    course_id = _uuid_text(row, "course_id", "material")
    if authorization_by_material.get(material_id) != course_id:
        raise LearningMaterialIntegrityError("Material does not match its authorization course")
    course = row.get("courses")
    if not isinstance(course, Mapping):
        raise LearningMaterialIntegrityError("Material is missing its canonical course")
    try:
        storage_provider = MaterialStorageProvider(_required_text(row, "storage_provider", "material"))
    except ValueError as error:
        raise LearningMaterialIntegrityError("Material has an unsupported storage provider") from error
    display_order = row.get("display_order")
    byte_size = row.get("byte_size")
    if type(display_order) is not int or display_order < 0:
        raise LearningMaterialIntegrityError("Material has invalid display order")
    if type(byte_size) is not int or byte_size <= 0:
        raise LearningMaterialIntegrityError("Material has invalid byte size")
    return AuthorizedLearningMaterial(
        material_id=material_id,
        university_id=university_id,
        study_plan_id=study_plan_id,
        course_id=course_id,
        course_code=_required_text(course, "course_code", "course"),
        course_name_ar=_optional_text(course.get("name_ar")),
        course_name_en=_optional_text(course.get("name_en")),
        title_ar=_required_text(row, "title_ar", "material"),
        title_en=_optional_text(row.get("title_en")),
        description_ar=_optional_text(row.get("description_ar")),
        description_en=_optional_text(row.get("description_en")),
        material_type=_required_text(row, "material_type", "material"),
        chapter_number=_optional_text(str(row["chapter_number"]) if row.get("chapter_number") is not None else None),
        display_order=display_order,
        file_name=_required_text(row, "file_name", "material"),
        mime_type=_required_text(row, "mime_type", "material"),
        byte_size=byte_size,
        sha256=_required_text(row, "sha256", "material"),
        storage_provider=storage_provider,
        storage_bucket=_optional_text(row.get("storage_bucket")),
        object_key=_required_text(row, "object_key", "material"),
        version_label=_required_text(row, "version_label", "material"),
    )


def _required_text(row: Mapping[str, Any], field: str, resource: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise LearningMaterialIntegrityError(f"{resource} is missing required {field}")
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise LearningMaterialIntegrityError("Material contains invalid optional text")
    return value


def _uuid_text(row: Mapping[str, Any], field: str, resource: str) -> str:
    try:
        return str(UUID(_required_text(row, field, resource)))
    except ValueError as error:
        raise LearningMaterialIntegrityError(f"{resource} has invalid {field}") from error
