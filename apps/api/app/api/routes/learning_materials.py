"""Authenticated student learning-material endpoints."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse, RedirectResponse

from app.core.auth import CurrentUser, get_current_user
from app.learning_materials.models import MaterialStorageProvider
from app.learning_materials.service import LearningMaterialService

router = APIRouter(
    prefix="/api/v1/me/learning-materials",
    tags=["learning-materials"],
    dependencies=[Depends(get_current_user)],
)
AuthenticatedUser = Annotated[CurrentUser, Depends(get_current_user)]


def _service(request: Request) -> LearningMaterialService:
    service = getattr(request.app.state, "learning_material_service", None)
    if service is None:
        raise HTTPException(503, "Learning material service unavailable")
    return service


@router.get("")
async def list_learning_materials(
    user: AuthenticatedUser, request: Request, response: Response
):
    materials = await _service(request).list_for_owner(user.user_id)
    grouped: dict[tuple[str, str, str | None, str | None], list[dict]] = defaultdict(list)
    for material in materials:
        key = (
            material.course_id,
            material.course_code,
            material.course_name_ar,
            material.course_name_en,
        )
        grouped[key].append({
            "material_id": material.material_id,
            "title_ar": material.title_ar,
            "title_en": material.title_en,
            "description_ar": material.description_ar,
            "description_en": material.description_en,
            "material_type": material.material_type,
            "chapter_number": material.chapter_number,
            "display_order": material.display_order,
            "file_name": material.file_name,
            "mime_type": material.mime_type,
            "byte_size": material.byte_size,
            "version_label": material.version_label,
            "download_path": f"/api/v1/me/learning-materials/{material.material_id}/download",
        })
    response.headers["Cache-Control"] = "private, no-store"
    return {
        "courses": [
            {
                "course_id": key[0],
                "course_code": key[1],
                "course_name_ar": key[2],
                "course_name_en": key[3],
                "materials": values,
            }
            for key, values in grouped.items()
        ],
        "coverage": "AUTHORIZED_ONLY",
    }


@router.get("/{material_id}/download")
async def download_learning_material(
    material_id: UUID,
    user: AuthenticatedUser,
    request: Request,
):
    service = _service(request)
    material = await service.get_for_owner(user.user_id, material_id)
    headers = {
        "Cache-Control": "private, no-store, max-age=0",
        "X-Content-Type-Options": "nosniff",
    }
    if material.storage_provider is MaterialStorageProvider.LOCAL_PRIVATE:
        file_path: Path = service.verified_local_path(material)
        return FileResponse(
            file_path,
            media_type=material.mime_type,
            filename=material.file_name,
            headers=headers,
        )
    url = await service.signed_storage_url(material)
    return RedirectResponse(url, status_code=307, headers=headers)
