"""Student-owned registration orchestration; Fake University remains mutation authority."""

from __future__ import annotations

import asyncio
from typing import Any

from app.university_sync.client import UniversityContractClient
from app.university_sync.identity_repository import SupabaseUniversityIdentityRepository
from app.university_sync.service import UniversitySyncService


class RegistrationUnavailableError(RuntimeError):
    pass


class RegistrationService:
    def __init__(
        self,
        client: UniversityContractClient,
        identities: SupabaseUniversityIdentityRepository,
        university_id: str,
        sync_service: UniversitySyncService | None = None,
    ) -> None:
        self._client = client
        self._identities = identities
        self._university_id = university_id
        self._sync_service = sync_service

    async def _token(self, owner_user_id: str) -> tuple[str, str]:
        identity = await self._identities.get_university_identity_for_user(
            owner_user_id, self._university_id
        )
        if identity is None:
            raise RegistrationUnavailableError("UNIVERSITY_IDENTITY_NOT_LINKED")
        token = await self._client.exchange_student_token(identity.university_student_id)
        return identity.university_student_id, token

    async def context(self, owner_user_id: str) -> dict[str, Any]:
        _, token = await self._token(owner_user_id)
        return await self._client.registration_request(
            "GET", "/api/integrations/morshidi/v1/student/registration/context", token
        )

    async def offerings(self, owner_user_id: str) -> dict[str, Any]:
        _, token = await self._token(owner_user_id)
        return await self._client.registration_request(
            "GET", "/api/integrations/morshidi/v1/student/registration/offerings", token
        )

    async def offering_context(
        self, owner_user_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Fetch current-term context and source provenance with one owner-scoped token."""
        _, token = await self._token(owner_user_id)
        context, manifest = await asyncio.gather(
            self._client.registration_request(
                "GET", "/api/integrations/morshidi/v1/student/registration/context", token
            ),
            self._client.source_manifest(token),
        )
        return context, manifest

    async def offering_source(
        self, owner_user_id: str,
    ) -> tuple[dict[str, Any], list[Any], dict[str, Any]]:
        """Fetch one complete, owner-scoped offerings view without mutation endpoints."""
        _, token = await self._token(owner_user_id)
        context, offerings_envelope, manifest = await asyncio.gather(
            self._client.registration_request(
                "GET", "/api/integrations/morshidi/v1/student/registration/context", token
            ),
            self._client.registration_request(
                "GET", "/api/integrations/morshidi/v1/student/registration/offerings", token
            ),
            self._client.source_manifest(token),
        )
        if offerings_envelope.get("success") is not True:
            raise RegistrationUnavailableError("UNIVERSITY_OFFERINGS_UNAVAILABLE")
        offerings = offerings_envelope.get("offerings")
        if not isinstance(offerings, list):
            raise RegistrationUnavailableError("UNIVERSITY_OFFERINGS_MALFORMED")
        return context, offerings, manifest

    async def preview(self, owner_user_id: str, section_ids: list[str]) -> dict[str, Any]:
        _, token = await self._token(owner_user_id)
        return await self._client.registration_request(
            "POST", "/api/integrations/morshidi/v1/student/registration/preview", token,
            payload={"sectionIds": section_ids},
        )

    async def register(
        self, owner_user_id: str, section_ids: list[str], idempotency_key: str
    ) -> dict[str, Any]:
        _, token = await self._token(owner_user_id)
        result = await self._client.registration_request(
            "POST", "/api/integrations/morshidi/v1/student/registration/register", token,
            payload={"sectionIds": section_ids}, idempotency_key=idempotency_key,
        )
        if result.get("success") is True and self._sync_service is not None:
            await self._sync_service.refresh_existing_student(owner_user_id, token)
        return result

    async def drop(
        self, owner_user_id: str, section_id: str, idempotency_key: str
    ) -> dict[str, Any]:
        _, token = await self._token(owner_user_id)
        result = await self._client.registration_request(
            "POST", "/api/integrations/morshidi/v1/student/registration/drop", token,
            payload={"sectionId": section_id}, idempotency_key=idempotency_key,
        )
        if result.get("success") is True and self._sync_service is not None:
            await self._sync_service.refresh_existing_student(owner_user_id, token)
        return result
