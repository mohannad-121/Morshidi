"""Supabase PostgREST repository for university tenants, integration configs, mappings, and jobs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import httpx

from .models import (
    ReconciliationItem,
    SyncJob,
    UniversityIntegrationConfig,
    UniversityMapping,
    UniversityTenant,
)


class SISIntegrationRepositoryError(RuntimeError):
    pass


class SupabaseSISIntegrationRepository:
    """PostgREST data access layer for SIS integration management."""

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
            raise SISIntegrationRepositoryError(f"Failed to query {resource}: {err}") from err
        if not 200 <= resp.status_code < 300:
            raise SISIntegrationRepositoryError(f"Query {resource} returned HTTP {resp.status_code}: {resp.text}")
        return resp.json()

    async def _post(self, resource: str, payload: dict[str, Any] | list[dict[str, Any]], *, prefer: str = "return=representation") -> list[dict[str, Any]]:
        try:
            resp = await self._client.post(
                f"{self._rest_url}/{resource}",
                json=payload,
                headers=self._headers(prefer=prefer),
                timeout=15,
            )
        except Exception as err:
            raise SISIntegrationRepositoryError(f"Failed to post to {resource}: {err}") from err
        if not 200 <= resp.status_code < 300:
            raise SISIntegrationRepositoryError(f"Post to {resource} returned HTTP {resp.status_code}: {resp.text}")
        if prefer.startswith("return=representation"):
            return resp.json()
        return []

    async def _patch(self, resource: str, params: Mapping[str, str], payload: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            resp = await self._client.patch(
                f"{self._rest_url}/{resource}",
                params=params,
                json=payload,
                headers=self._headers(prefer="return=representation"),
                timeout=15,
            )
        except Exception as err:
            raise SISIntegrationRepositoryError(f"Failed to patch {resource}: {err}") from err
        if not 200 <= resp.status_code < 300:
            raise SISIntegrationRepositoryError(f"Patch {resource} returned HTTP {resp.status_code}: {resp.text}")
        return resp.json()

    async def _delete(self, resource: str, params: Mapping[str, str]) -> bool:
        try:
            resp = await self._client.delete(
                f"{self._rest_url}/{resource}",
                params=params,
                headers=self._headers(),
                timeout=15,
            )
        except Exception as err:
            raise SISIntegrationRepositoryError(f"Failed to delete {resource}: {err}") from err
        return 200 <= resp.status_code < 300

    # --- University Tenant Operations ---

    async def get_university_by_id(self, university_id: UUID) -> UniversityTenant | None:
        rows = await self._get("universities", {"id": f"eq.{university_id}", "select": "*"})
        if not rows:
            return None
        return UniversityTenant.model_validate(rows[0])

    async def get_university_by_tenant_key(self, tenant_key: str) -> UniversityTenant | None:
        rows = await self._get("universities", {"tenant_key": f"eq.{tenant_key}", "select": "*"})
        if not rows:
            return None
        return UniversityTenant.model_validate(rows[0])

    async def list_universities(self) -> list[UniversityTenant]:
        rows = await self._get("universities", {"select": "*", "order": "name_ar.asc"})
        return [UniversityTenant.model_validate(r) for r in rows]

    # --- University Integration Config Operations ---

    async def get_integration_config(
        self, university_id: UUID, provider_type: str | None = None
    ) -> UniversityIntegrationConfig | None:
        params: dict[str, str] = {"university_id": f"eq.{university_id}", "select": "*"}
        if provider_type:
            params["provider_type"] = f"eq.{provider_type}"
        rows = await self._get("university_integration_configs", params)
        if not rows:
            return None
        return UniversityIntegrationConfig.model_validate(rows[0])

    async def upsert_integration_config(self, config: UniversityIntegrationConfig) -> UniversityIntegrationConfig:
        payload = config.model_dump(mode="json", exclude={"id", "created_at", "updated_at"})
        rows = await self._post(
            "university_integration_configs",
            payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return UniversityIntegrationConfig.model_validate(rows[0])

    # --- Mapping Operations ---

    async def list_mappings(
        self, university_id: UUID, entity_type: str | None = None
    ) -> list[UniversityMapping]:
        params: dict[str, str] = {"university_id": f"eq.{university_id}", "select": "*"}
        if entity_type:
            params["entity_type"] = f"eq.{entity_type.upper()}"
        rows = await self._get("university_mappings", params)
        return [UniversityMapping.model_validate(r) for r in rows]

    async def upsert_mapping(self, mapping: UniversityMapping) -> UniversityMapping:
        payload = mapping.model_dump(mode="json", exclude={"id"})
        rows = await self._post(
            "university_mappings",
            payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return UniversityMapping.model_validate(rows[0])

    async def bulk_upsert_mappings(self, mappings: list[UniversityMapping]) -> int:
        if not mappings:
            return 0
        payload = [m.model_dump(mode="json", exclude={"id"}) for m in mappings]
        rows = await self._post(
            "university_mappings",
            payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return len(rows)

    async def delete_mapping(self, mapping_id: UUID) -> bool:
        return await self._delete("university_mappings", {"id": f"eq.{mapping_id}"})

    # --- Sync Job Operations ---

    async def create_sync_job(self, job: SyncJob) -> SyncJob:
        payload = job.model_dump(mode="json", exclude={"id"})
        rows = await self._post("university_sync_jobs", payload)
        return SyncJob.model_validate(rows[0])

    async def update_sync_job(self, job: SyncJob) -> SyncJob:
        if not job.id:
            raise ValueError("Cannot update sync job without ID")
        payload = job.model_dump(mode="json", exclude={"id", "university_id", "started_at"})
        rows = await self._patch("university_sync_jobs", {"id": f"eq.{job.id}"}, payload)
        return SyncJob.model_validate(rows[0])

    async def get_latest_sync_job(self, university_id: UUID) -> SyncJob | None:
        rows = await self._get("university_sync_jobs", {
            "university_id": f"eq.{university_id}",
            "select": "*",
            "order": "started_at.desc",
            "limit": "1",
        })
        if not rows:
            return None
        return SyncJob.model_validate(rows[0])

    async def list_sync_jobs(self, university_id: UUID, limit: int = 20) -> list[SyncJob]:
        rows = await self._get("university_sync_jobs", {
            "university_id": f"eq.{university_id}",
            "select": "*",
            "order": "started_at.desc",
            "limit": str(limit),
        })
        return [SyncJob.model_validate(r) for r in rows]

    # --- Reconciliation Operations ---

    async def record_reconciliation_item(self, item: ReconciliationItem) -> ReconciliationItem:
        payload = item.model_dump(mode="json", exclude={"id"})
        rows = await self._post("university_reconciliation_items", payload)
        return ReconciliationItem.model_validate(rows[0])

    async def list_reconciliation_items(
        self, university_id: UUID, status: str | None = None
    ) -> list[ReconciliationItem]:
        params: dict[str, str] = {"university_id": f"eq.{university_id}", "select": "*"}
        if status:
            params["status"] = f"eq.{status}"
        rows = await self._get("university_reconciliation_items", params)
        return [ReconciliationItem.model_validate(r) for r in rows]

    # --- Audit Log Operations ---

    async def log_audit_event(
        self,
        university_id: UUID,
        action: str,
        details: dict[str, Any],
        actor_user_id: UUID | None = None,
    ) -> None:
        payload = {
            "university_id": str(university_id),
            "action": action,
            "details": details,
            "actor_user_id": str(actor_user_id) if actor_user_id else None,
        }
        await self._post("university_integration_audit_log", payload, prefer="return=minimal")

