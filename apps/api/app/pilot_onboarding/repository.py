"""PostgREST data access layer for university pilot onboarding."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import httpx

from .models import (
    PilotAcceptanceCheck,
    PilotActivity,
    PilotBlocker,
    PilotRequirement,
    PilotSignoff,
    PilotStakeholder,
    UniversityPilot,
)


class PilotRepositoryError(RuntimeError):
    pass


class PilotRepository:
    """Data access layer for university pilot onboarding entities."""

    def __init__(self, supabase_url: str, server_key: str, client: httpx.AsyncClient | None = None) -> None:
        if not supabase_url.strip() or not server_key.strip():
            raise ValueError("supabase_url and server_key are required")
        self._rest_url = f"{supabase_url.rstrip('/')}/rest/v1"
        self._server_key = server_key
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self._server_key,
            "Authorization": f"Bearer {self._server_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    async def _get(self, resource: str, params: Mapping[str, str]) -> list[dict[str, Any]]:
        try:
            resp = await self._client.get(
                f"{self._rest_url}/{resource}",
                params=params,
                headers=self._headers(),
                timeout=15,
            )
        except Exception as err:
            raise PilotRepositoryError(f"Failed to query {resource}: {err}") from err
        if not 200 <= resp.status_code < 300:
            raise PilotRepositoryError(f"Error querying {resource} ({resp.status_code}): {resp.text}")
        try:
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as err:
            raise PilotRepositoryError(f"Malformed JSON from {resource}: {err}") from err

    async def _post(self, resource: str, payload: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        try:
            resp = await self._client.post(
                f"{self._rest_url}/{resource}",
                headers=self._headers(prefer="return=representation"),
                json=payload,
                timeout=15,
            )
        except Exception as err:
            raise PilotRepositoryError(f"Failed to insert into {resource}: {err}") from err
        if not 200 <= resp.status_code < 300:
            raise PilotRepositoryError(f"Error inserting into {resource} ({resp.status_code}): {resp.text}")
        try:
            data = resp.json()
            return data if isinstance(data, list) else [data]
        except Exception as err:
            raise PilotRepositoryError(f"Malformed JSON on insert into {resource}: {err}") from err

    async def _patch(self, resource: str, params: Mapping[str, str], payload: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            resp = await self._client.patch(
                f"{self._rest_url}/{resource}",
                params=params,
                headers=self._headers(prefer="return=representation"),
                json=payload,
                timeout=15,
            )
        except Exception as err:
            raise PilotRepositoryError(f"Failed to patch {resource}: {err}") from err
        if not 200 <= resp.status_code < 300:
            raise PilotRepositoryError(f"Error patching {resource} ({resp.status_code}): {resp.text}")
        try:
            data = resp.json()
            return data if isinstance(data, list) else [data]
        except Exception as err:
            raise PilotRepositoryError(f"Malformed JSON on patch {resource}: {err}") from err

    async def _delete(self, resource: str, params: Mapping[str, str]) -> None:
        try:
            resp = await self._client.delete(
                f"{self._rest_url}/{resource}",
                params=params,
                headers=self._headers(),
                timeout=15,
            )
        except Exception as err:
            raise PilotRepositoryError(f"Failed to delete from {resource}: {err}") from err
        if not 200 <= resp.status_code < 300:
            raise PilotRepositoryError(f"Error deleting from {resource} ({resp.status_code}): {resp.text}")

    # =========================================================================
    # Pilots CRUD
    # =========================================================================

    async def create_pilot(self, pilot: UniversityPilot) -> UniversityPilot:
        data = pilot.model_dump(mode="json")
        res = await self._post("university_pilots", data)
        if not res:
            raise PilotRepositoryError("Failed to persist pilot record")
        return UniversityPilot.model_validate(res[0])

    async def get_pilot(self, pilot_id: UUID) -> UniversityPilot | None:
        rows = await self._get("university_pilots", {"id": f"eq.{pilot_id}", "limit": "1"})
        return UniversityPilot.model_validate(rows[0]) if rows else None

    async def list_pilots(self, university_id: UUID | None = None) -> list[UniversityPilot]:
        params = {"order": "created_at.desc"}
        if university_id:
            params["university_id"] = f"eq.{university_id}"
        rows = await self._get("university_pilots", params)
        return [UniversityPilot.model_validate(r) for r in rows]

    async def update_pilot(self, pilot_id: UUID, updates: dict[str, Any]) -> UniversityPilot:
        res = await self._patch("university_pilots", {"id": f"eq.{pilot_id}"}, updates)
        if not res:
            raise PilotRepositoryError(f"Pilot {pilot_id} not found for update")
        return UniversityPilot.model_validate(res[0])

    # =========================================================================
    # Stakeholders
    # =========================================================================

    async def list_stakeholders(self, pilot_id: UUID) -> list[PilotStakeholder]:
        rows = await self._get("university_pilot_stakeholders", {"pilot_id": f"eq.{pilot_id}", "order": "created_at.asc"})
        return [PilotStakeholder.model_validate(r) for r in rows]

    async def add_stakeholder(self, stakeholder: PilotStakeholder) -> PilotStakeholder:
        res = await self._post("university_pilot_stakeholders", stakeholder.model_dump(mode="json"))
        return PilotStakeholder.model_validate(res[0])

    async def delete_stakeholder(self, stakeholder_id: UUID) -> None:
        await self._delete("university_pilot_stakeholders", {"id": f"eq.{stakeholder_id}"})

    # =========================================================================
    # Requirements
    # =========================================================================

    async def list_requirements(self, pilot_id: UUID) -> list[PilotRequirement]:
        rows = await self._get("university_pilot_requirements", {"pilot_id": f"eq.{pilot_id}", "order": "created_at.asc"})
        return [PilotRequirement.model_validate(r) for r in rows]

    async def bulk_init_requirements(self, pilot_id: UUID, items: list[dict[str, Any]]) -> list[PilotRequirement]:
        payloads = [dict(item, pilot_id=str(pilot_id)) for item in items]
        res = await self._post("university_pilot_requirements", payloads)
        return [PilotRequirement.model_validate(r) for r in res]

    async def update_requirement(self, pilot_id: UUID, requirement_key: str, updates: dict[str, Any]) -> PilotRequirement:
        res = await self._patch(
            "university_pilot_requirements",
            {"pilot_id": f"eq.{pilot_id}", "requirement_key": f"eq.{requirement_key}"},
            updates,
        )
        if not res:
            raise PilotRepositoryError(f"Requirement {requirement_key} not found for pilot {pilot_id}")
        return PilotRequirement.model_validate(res[0])

    # =========================================================================
    # Blockers
    # =========================================================================

    async def list_blockers(self, pilot_id: UUID) -> list[PilotBlocker]:
        rows = await self._get("university_pilot_blockers", {"pilot_id": f"eq.{pilot_id}", "order": "created_at.desc"})
        return [PilotBlocker.model_validate(r) for r in rows]

    async def add_blocker(self, blocker: PilotBlocker) -> PilotBlocker:
        res = await self._post("university_pilot_blockers", blocker.model_dump(mode="json"))
        return PilotBlocker.model_validate(res[0])

    async def update_blocker(self, blocker_id: UUID, updates: dict[str, Any]) -> PilotBlocker:
        res = await self._patch("university_pilot_blockers", {"id": f"eq.{blocker_id}"}, updates)
        if not res:
            raise PilotRepositoryError(f"Blocker {blocker_id} not found for update")
        return PilotBlocker.model_validate(res[0])

    # =========================================================================
    # Acceptance Checks
    # =========================================================================

    async def list_acceptance_checks(self, pilot_id: UUID) -> list[PilotAcceptanceCheck]:
        rows = await self._get("university_pilot_acceptance_checks", {"pilot_id": f"eq.{pilot_id}", "order": "created_at.asc"})
        return [PilotAcceptanceCheck.model_validate(r) for r in rows]

    async def bulk_init_acceptance_checks(self, pilot_id: UUID, items: list[dict[str, Any]]) -> list[PilotAcceptanceCheck]:
        payloads = [dict(item, pilot_id=str(pilot_id)) for item in items]
        res = await self._post("university_pilot_acceptance_checks", payloads)
        return [PilotAcceptanceCheck.model_validate(r) for r in res]

    async def update_acceptance_check(self, pilot_id: UUID, check_key: str, updates: dict[str, Any]) -> PilotAcceptanceCheck:
        res = await self._patch(
            "university_pilot_acceptance_checks",
            {"pilot_id": f"eq.{pilot_id}", "check_key": f"eq.{check_key}"},
            updates,
        )
        if not res:
            raise PilotRepositoryError(f"Acceptance check {check_key} not found for pilot {pilot_id}")
        return PilotAcceptanceCheck.model_validate(res[0])

    # =========================================================================
    # Sign-offs
    # =========================================================================

    async def list_signoffs(self, pilot_id: UUID) -> list[PilotSignoff]:
        rows = await self._get("university_pilot_signoffs", {"pilot_id": f"eq.{pilot_id}", "order": "created_at.asc"})
        return [PilotSignoff.model_validate(r) for r in rows]

    async def record_signoff(self, signoff: PilotSignoff) -> PilotSignoff:
        # Check if already exists for upsert behavior
        existing = await self._get(
            "university_pilot_signoffs",
            {"pilot_id": f"eq.{signoff.pilot_id}", "signoff_role": f"eq.{signoff.signoff_role.value}"},
        )
        if existing:
            res = await self._patch(
                "university_pilot_signoffs",
                {"id": f"eq.{existing[0]['id']}"},
                signoff.model_dump(mode="json", exclude={"id", "created_at"}),
            )
            return PilotSignoff.model_validate(res[0])
        res = await self._post("university_pilot_signoffs", signoff.model_dump(mode="json"))
        return PilotSignoff.model_validate(res[0])

    # =========================================================================
    # Activity Log
    # =========================================================================

    async def list_activity(self, pilot_id: UUID) -> list[PilotActivity]:
        rows = await self._get("university_pilot_activity", {"pilot_id": f"eq.{pilot_id}", "order": "created_at.desc"})
        return [PilotActivity.model_validate(r) for r in rows]

    async def log_activity(
        self,
        pilot_id: UUID,
        action: str,
        *,
        actor_id: UUID | None = None,
        actor_email: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "pilot_id": str(pilot_id),
            "action": action,
            "actor_id": str(actor_id) if actor_id else None,
            "actor_email": actor_email,
            "details": details or {},
        }
        await self._post("university_pilot_activity", payload)
