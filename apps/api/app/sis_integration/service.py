"""Unified SIS integration domain service coordinating adapters, mappings, sync, and readiness."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from app.university_sync.client import UniversityContractClient

from .adapter_interface import SISAdapter
from .adapter_registry import AdapterRegistry
from .capabilities import CapabilityNegotiator, PilotMode, SISCapability, TenantStatus
from .errors import (
    CapabilityNotSupportedError,
    IdentityNotFoundError,
    MappingMissingError,
    SISIntegrationError,
    WriteActionNotAllowedError,
)
from .health import IntegrationHealthEvaluator
from .mapping_layer import MappingLayer
from .models import (
    HealthResult,
    PilotReadinessScorecard,
    ReconciliationItem,
    SyncJob,
    UniversityIntegrationConfig,
    UniversityMapping,
    UniversityTenant,
)
from .pilot_readiness import PilotReadinessEvaluator
from .reconciliation import ReconciliationEngine
from .repository import SupabaseSISIntegrationRepository
from .security import mask_secret_status, resolve_secret, validate_target_url
from .sync_orchestrator import SyncOrchestrator
from .webhook_engine import WebhookEngine


class SISIntegrationService:
    """Unified service for university tenant SIS integration, readiness, and synchronization."""

    def __init__(
        self,
        repository: SupabaseSISIntegrationRepository,
        *,
        http_client: httpx.AsyncClient | None = None,
        allow_localhost: bool = False,
    ) -> None:
        self.repository = repository
        self._http = http_client
        self._allow_localhost = allow_localhost
        self._webhook_engine = WebhookEngine()

    async def get_tenant_by_id(self, university_id: UUID) -> UniversityTenant:
        tenant = await self.repository.get_university_by_id(university_id)
        if not tenant:
            raise SISIntegrationError("TENANT_NOT_FOUND", f"University tenant '{university_id}' not found", 404)
        return tenant

    async def get_tenant_by_key(self, tenant_key: str) -> UniversityTenant:
        tenant = await self.repository.get_university_by_tenant_key(tenant_key)
        if not tenant:
            raise SISIntegrationError("TENANT_NOT_FOUND", f"University tenant key '{tenant_key}' not found", 404)
        return tenant

    async def list_tenants(self) -> list[UniversityTenant]:
        return await self.repository.list_universities()

    async def get_config(self, university_id: UUID) -> UniversityIntegrationConfig | None:
        return await self.repository.get_integration_config(university_id)

    async def save_config(
        self,
        config: UniversityIntegrationConfig,
        actor_user_id: UUID | None = None,
    ) -> UniversityIntegrationConfig:
        # Validate SSRF
        validate_target_url(config.base_url, allow_localhost=self._allow_localhost)
        saved = await self.repository.upsert_integration_config(config)
        await self.repository.log_audit_event(
            config.university_id,
            "UPSERT_INTEGRATION_CONFIG",
            {"provider_type": config.provider_type, "base_url": config.base_url, "pilot_mode": config.pilot_mode.value},
            actor_user_id=actor_user_id,
        )
        return saved

    async def get_adapter_for_tenant(self, university_id: UUID) -> tuple[SISAdapter, UniversityIntegrationConfig]:
        config = await self.repository.get_integration_config(university_id)
        if not config or not config.active:
            raise SISIntegrationError("INTEGRATION_NOT_ACTIVE", "University integration is not active or configured", 400)

        adapter = AdapterRegistry.get_adapter(
            config,
            http_client=self._http,
            allow_localhost=self._allow_localhost,
        )
        return adapter, config

    async def get_mapping_layer(self, university_id: UUID) -> MappingLayer:
        mappings = await self.repository.list_mappings(university_id)
        return MappingLayer(university_id, mappings)

    async def get_health(self, university_id: UUID) -> HealthResult:
        config = await self.repository.get_integration_config(university_id)
        if not config:
            return HealthResult(
                status="NOT_CONFIGURED",
                connectivity=False,
                latency_ms=0.0,
                details={"reason": "No integration configuration found"},
            )

        last_job = await self.repository.get_latest_sync_job(university_id)
        last_job_dict = last_job.model_dump(mode="json") if last_job else None

        try:
            adapter = AdapterRegistry.get_adapter(
                config,
                http_client=self._http,
                allow_localhost=self._allow_localhost,
            )
            return await IntegrationHealthEvaluator.evaluate_health(
                adapter, config, last_sync_job=last_job_dict
            )
        except Exception as err:
            return HealthResult(
                status="UNHEALTHY",
                connectivity=False,
                latency_ms=0.0,
                details={"error": str(err)},
            )

    async def get_readiness_scorecard(self, university_id: UUID) -> PilotReadinessScorecard:
        tenant = await self.get_tenant_by_id(university_id)
        config = await self.repository.get_integration_config(university_id)
        health = await self.get_health(university_id)
        mapping_layer = await self.get_mapping_layer(university_id)

        # Collect known entities or mock canonical baseline
        # In multi-plan foundation, we have 17 plans, 17 majors, 7 faculties
        known_entities = {
            "faculty": ["IT", "SCI", "ARTS", "BUS", "MEDIA", "LAW", "NURS"],
            "major": ["AI", "SE", "CS", "CYBER", "MATH", "PHYS", "ARABIC", "ENGLISH", "HISTORY", "TRANS", "ECON", "BBA", "ACC", "DJOURN", "RTV", "LAW", "NURS"],
            "plan": [f"ZU:{f}:{m}:P12" for f, m in [
                ("IT", "AI"), ("IT", "SE"), ("IT", "CS"), ("IT", "CYBER"),
                ("SCI", "MATH"), ("SCI", "PHYS"),
                ("ARTS", "ARABIC"), ("ARTS", "ENGLISH"), ("ARTS", "HISTORY"), ("ARTS", "TRANS"),
                ("BUS", "ECON"), ("BUS", "BBA"), ("BUS", "ACC"),
                ("MEDIA", "DJOURN"), ("MEDIA", "RTV"),
                ("LAW", "LAW"), ("NURS", "NURS"),
            ]],
            "course": ["CS101", "CS102", "MATH101", "SE201", "AI201"],
            "term": ["2026-1", "CURRENT"],
        }

        jobs = await self.repository.list_sync_jobs(university_id, limit=5)
        recent_success = any(j.status == "SUCCEEDED" for j in jobs)

        return PilotReadinessEvaluator.evaluate(
            tenant,
            config,
            health,
            mapping_layer,
            known_entities,
            sync_job_count=len(jobs),
            recent_sync_succeeded=recent_success,
        )

    async def list_mappings(
        self, university_id: UUID, entity_type: str | None = None
    ) -> list[UniversityMapping]:
        return await self.repository.list_mappings(university_id, entity_type)

    async def save_mapping(
        self,
        mapping: UniversityMapping,
        actor_user_id: UUID | None = None,
    ) -> UniversityMapping:
        saved = await self.repository.upsert_mapping(mapping)
        await self.repository.log_audit_event(
            mapping.university_id,
            "UPSERT_MAPPING",
            {
                "entity_type": mapping.entity_type,
                "external_code": mapping.external_code,
                "canonical_id": mapping.canonical_id,
            },
            actor_user_id=actor_user_id,
        )
        return saved

    async def delete_mapping(
        self,
        university_id: UUID,
        mapping_id: UUID,
        actor_user_id: UUID | None = None,
    ) -> bool:
        deleted = await self.repository.delete_mapping(mapping_id)
        if deleted:
            await self.repository.log_audit_event(
                university_id,
                "DELETE_MAPPING",
                {"mapping_id": str(mapping_id)},
                actor_user_id=actor_user_id,
            )
        return deleted

    async def trigger_sync(
        self,
        university_id: UUID,
        mode: str = "FULL_SYNC",
        cursor: str | None = None,
        actor_user_id: UUID | None = None,
    ) -> SyncJob:
        adapter, config = await self.get_adapter_for_tenant(university_id)
        mapping_layer = await self.get_mapping_layer(university_id)

        orchestrator = SyncOrchestrator(
            university_id=university_id,
            adapter=adapter,
            mapping_layer=mapping_layer,
        )

        # Log job initiation
        pending_job = SyncJob(
            university_id=university_id,
            sync_mode=mode,  # type: ignore[arg-type]
            status="RUNNING",
            cursor_before=cursor,
        )
        created_job = await self.repository.create_sync_job(pending_job)

        try:
            if mode == "FULL_SYNC":
                completed_job = await orchestrator.run_full_sync()
            elif mode == "INCREMENTAL_SYNC":
                completed_job = await orchestrator.run_incremental_sync(cursor)
            else:
                raise SISIntegrationError("INVALID_SYNC_MODE", f"Unsupported sync mode '{mode}'", 400)

            completed_job.id = created_job.id
            saved_job = await self.repository.update_sync_job(completed_job)

            await self.repository.log_audit_event(
                university_id,
                "EXECUTE_SYNC",
                {
                    "job_id": str(saved_job.id),
                    "mode": mode,
                    "status": saved_job.status,
                    "processed": saved_job.records_processed,
                },
                actor_user_id=actor_user_id,
            )
            return saved_job
        except Exception as err:
            created_job.status = "FAILED"
            created_job.errors.append(str(err))
            await self.repository.update_sync_job(created_job)
            raise

    async def list_sync_jobs(self, university_id: UUID, limit: int = 20) -> list[SyncJob]:
        return await self.repository.list_sync_jobs(university_id, limit=limit)

    async def list_reconciliation_items(
        self, university_id: UUID, status: str | None = None
    ) -> list[ReconciliationItem]:
        return await self.repository.list_reconciliation_items(university_id, status=status)

    async def handle_inbound_webhook(
        self,
        tenant_key: str,
        provider: str,
        raw_body: bytes,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        tenant = await self.get_tenant_by_key(tenant_key)
        config = await self.repository.get_integration_config(tenant.id)
        if not config or not config.active:
            raise SISIntegrationError("INTEGRATION_NOT_ACTIVE", "Integration is not configured or disabled", 400)

        # Check capability
        if SISCapability.WEBHOOKS not in config.supported_capabilities:
            raise CapabilityNotSupportedError("Tenant has not enabled WEBHOOKS capability")

        # Resolve webhook secret
        secret = resolve_secret(config.webhook_secret_env_ref)
        if not secret:
            raise SISIntegrationError("WEBHOOK_SECRET_UNCONFIGURED", "Webhook secret is not configured in server environment", 500)

        # Process through webhook engine
        result = self._webhook_engine.process_inbound_webhook(
            raw_body=raw_body,
            headers=headers,
            webhook_secret=secret,
        )

        await self.repository.log_audit_event(
            tenant.id,
            "INGEST_WEBHOOK",
            {"provider": provider, "status": result["status"], "event_id": result.get("event_id")},
        )
        return result

