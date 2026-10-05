"""Supabase data-access adapter for student_university_identities table.

This repository runs server-side with the Supabase service role key to manage
mappings between internal Morshidi users (auth.users) and external university
student IDs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StudentUniversityIdentityRecord:
    """Internal representation of a student_university_identities row."""

    id: str
    owner_user_id: str
    university_id: str
    university_student_id: str
    created_at: datetime
    updated_at: datetime
    last_synced_at: datetime | None = None


class UniversityIdentityError(Exception):
    """Base exception for university identity mapping operations."""


class UniversityIdentityNotFoundError(UniversityIdentityError):
    """Raised when an identity mapping is not found."""


class UniversityIdentityConflictError(UniversityIdentityError):
    """Raised when an identity mapping violates a uniqueness constraint (e.g. concurrent race)."""


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _row_to_record(row: dict[str, Any]) -> StudentUniversityIdentityRecord:
    return StudentUniversityIdentityRecord(
        id=str(row["id"]),
        owner_user_id=str(row["owner_user_id"]),
        university_id=str(row["university_id"]),
        university_student_id=str(row["university_student_id"]),
        created_at=_parse_iso_datetime(row.get("created_at")) or datetime.now(timezone.utc),
        updated_at=_parse_iso_datetime(row.get("updated_at")) or datetime.now(timezone.utc),
        last_synced_at=_parse_iso_datetime(row.get("last_synced_at")),
    )


class SupabaseUniversityIdentityRepository:
    """Server-side service-role repository for student_university_identities."""

    def __init__(
        self,
        supabase_url: str,
        service_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not supabase_url.strip() or not service_key.strip():
            raise ValueError("supabase_url and service_key must not be empty")
        self._rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._service_key = service_key
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self._service_key,
            "Authorization": f"Bearer {self._service_key}",
            "Accept": "application/json",
        }

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def get_university_identity(
        self,
        university_id: UUID | str,
        university_student_id: str,
    ) -> StudentUniversityIdentityRecord | None:
        """Find an identity mapping by external university_id and university_student_id.

        Preserves university_student_id as string.
        """
        response = await self._client.get(
            f"{self._rest_url}/student_university_identities",
            params={
                "select": "id,owner_user_id,university_id,university_student_id,created_at,updated_at,last_synced_at",
                "university_id": f"eq.{str(university_id)}",
                "university_student_id": f"eq.{str(university_student_id)}",
                "limit": "1",
            },
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        rows = response.json()
        if not rows or not isinstance(rows, list):
            return None
        return _row_to_record(rows[0])

    async def get_university_identity_for_user(
        self,
        owner_user_id: UUID | str,
        university_id: UUID | str,
    ) -> StudentUniversityIdentityRecord | None:
        """Find an identity mapping for an internal Morshidi user and university_id."""
        response = await self._client.get(
            f"{self._rest_url}/student_university_identities",
            params={
                "select": "id,owner_user_id,university_id,university_student_id,created_at,updated_at,last_synced_at",
                "owner_user_id": f"eq.{str(owner_user_id)}",
                "university_id": f"eq.{str(university_id)}",
                "limit": "1",
            },
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        rows = response.json()
        if not rows or not isinstance(rows, list):
            return None
        return _row_to_record(rows[0])

    async def create_or_link_university_identity(
        self,
        owner_user_id: UUID | str,
        university_id: UUID | str,
        university_student_id: str,
    ) -> StudentUniversityIdentityRecord:
        """Create a new mapping between a Morshidi user and an external university student ID.

        Enforces database uniqueness:
        - UNIQUE(university_id, university_student_id)
        - UNIQUE(owner_user_id, university_id)

        Raises UniversityIdentityConflictError on duplicate / race condition.
        """
        payload = {
            "owner_user_id": str(owner_user_id),
            "university_id": str(university_id),
            "university_student_id": str(university_student_id).strip(),
        }
        response = await self._client.post(
            f"{self._rest_url}/student_university_identities",
            params={"select": "id,owner_user_id,university_id,university_student_id,created_at,updated_at,last_synced_at"},
            headers={
                **self._headers(),
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            json=payload,
            timeout=10,
        )

        if response.status_code == 409:
            body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
            code = body.get("code") or ""
            message = body.get("message") or "Identity mapping uniqueness violation"
            raise UniversityIdentityConflictError(f"Duplicate university identity ({code}): {message}")

        response.raise_for_status()
        rows = response.json()
        if not rows or not isinstance(rows, list):
            raise UniversityIdentityError("Unexpected response payload when creating university identity")
        return _row_to_record(rows[0])

    async def touch_last_synced_at(
        self,
        identity_id: UUID | str,
        last_synced_at: datetime | None = None,
    ) -> None:
        """Update last_synced_at timestamp for an existing mapping."""
        synced = (last_synced_at or datetime.now(timezone.utc)).isoformat()
        response = await self._client.patch(
            f"{self._rest_url}/student_university_identities",
            params={"id": f"eq.{str(identity_id)}"},
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"last_synced_at": synced},
            timeout=10,
        )
        response.raise_for_status()
