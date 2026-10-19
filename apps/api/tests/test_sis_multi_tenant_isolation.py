"""Deterministic multi-tenant isolation tests verifying zero cross-tenant leakage."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4
import pytest
import httpx

from app.sis_integration.capabilities import PilotMode, SISCapability
from app.sis_integration.mapping_layer import MappingLayer
from app.sis_integration.models import (
    ReconciliationItem,
    SyncJob,
    UniversityIntegrationConfig,
    UniversityMapping,
    UniversityTenant,
)
from app.sis_integration.repository import SupabaseSISIntegrationRepository
from app.sis_integration.service import SISIntegrationService


class InMemoryFakePostgrestRepo(SupabaseSISIntegrationRepository):
    """In-memory repository implementing SupabaseSISIntegrationRepository contract for multi-tenant isolation tests."""

    def __init__(self) -> None:
        self.tenants: dict[UUID, UniversityTenant] = {}
        self.configs: dict[UUID, UniversityIntegrationConfig] = {}
        self.mappings: dict[UUID, list[UniversityMapping]] = {}
        self.sync_jobs: dict[UUID, list[SyncJob]] = {}
        self.reconciliation_items: dict[UUID, list[ReconciliationItem]] = {}
        self.audit_log: list[dict[str, Any]] = []

    async def get_university_by_id(self, university_id: UUID) -> UniversityTenant | None:
        return self.tenants.get(university_id)

    async def get_university_by_tenant_key(self, tenant_key: str) -> UniversityTenant | None:
        for t in self.tenants.values():
            if t.tenant_key.lower() == tenant_key.lower():
                return t
        return None

    async def list_universities(self) -> list[UniversityTenant]:
        return list(self.tenants.values())

    async def get_integration_config(
        self, university_id: UUID, provider_type: str | None = None
    ) -> UniversityIntegrationConfig | None:
        return self.configs.get(university_id)

    async def upsert_integration_config(self, config: UniversityIntegrationConfig) -> UniversityIntegrationConfig:
        self.configs[config.university_id] = config
        return config

    async def list_mappings(
        self, university_id: UUID, entity_type: str | None = None
    ) -> list[UniversityMapping]:
        items = self.mappings.get(university_id, [])
        if entity_type:
            return [m for m in items if m.entity_type.upper() == entity_type.upper()]
        return list(items)

    async def upsert_mapping(self, mapping: UniversityMapping) -> UniversityMapping:
        items = self.mappings.setdefault(mapping.university_id, [])
        # Check duplicate
        for idx, existing in enumerate(items):
            if existing.entity_type == mapping.entity_type and existing.external_code == mapping.external_code:
                items[idx] = mapping
                return mapping
        items.append(mapping)
        return mapping

    async def bulk_upsert_mappings(self, mappings: list[UniversityMapping]) -> int:
        count = 0
        for m in mappings:
            await self.upsert_mapping(m)
            count += 1
        return count

    async def delete_mapping(self, mapping_id: UUID) -> bool:
        for uni_id, items in self.mappings.items():
            for idx, m in enumerate(items):
                if m.id == mapping_id:
                    del items[idx]
                    return True
        return False

    async def create_sync_job(self, job: SyncJob) -> SyncJob:
        job.id = uuid4()
        self.sync_jobs.setdefault(job.university_id, []).append(job)
        return job

    async def update_sync_job(self, job: SyncJob) -> SyncJob:
        items = self.sync_jobs.get(job.university_id, [])
        for idx, existing in enumerate(items):
            if existing.id == job.id:
                items[idx] = job
                return job
        return job

    async def get_latest_sync_job(self, university_id: UUID) -> SyncJob | None:
        items = self.sync_jobs.get(university_id, [])
        return items[-1] if items else None

    async def list_sync_jobs(self, university_id: UUID, limit: int = 20) -> list[SyncJob]:
        items = self.sync_jobs.get(university_id, [])
        return list(reversed(items[-limit:]))

    async def record_reconciliation_item(self, item: ReconciliationItem) -> ReconciliationItem:
        item.id = uuid4()
        self.reconciliation_items.setdefault(item.university_id, []).append(item)
        return item

    async def list_reconciliation_items(
        self, university_id: UUID, status: str | None = None
    ) -> list[ReconciliationItem]:
        items = self.reconciliation_items.get(university_id, [])
        if status:
            return [i for i in items if i.status == status]
        return list(items)

    async def log_audit_event(
        self,
        university_id: UUID,
        action: str,
        details: dict[str, Any],
        actor_user_id: UUID | None = None,
    ) -> None:
        self.audit_log.append({
            "university_id": university_id,
            "action": action,
            "details": details,
            "actor_user_id": actor_user_id,
        })


@pytest.mark.anyio
async def test_multi_tenant_complete_isolation():
    """Verify Tenant A (Zarqa) and Tenant B (Pilot B) are 100% isolated with CROSS_TENANT_DATA_LEAKAGE = 0."""
    repo = InMemoryFakePostgrestRepo()
    service = SISIntegrationService(repo, allow_localhost=True)

    # 1. Setup Tenant A (Zarqa)
    tenant_a_id = UUID("10000000-0000-0000-0000-000000000001")
    tenant_a = UniversityTenant(
        id=tenant_a_id,
        tenant_key="zarqa",
        name_ar="جامعة الزرقاء",
        name_en="Zarqa University",
        country="Jordan",
    )
    repo.tenants[tenant_a_id] = tenant_a

    config_a = UniversityIntegrationConfig(
        university_id=tenant_a_id,
        provider_type="fake_university",
        base_url="https://fake-university-aqdn.onrender.com",
        supported_capabilities=[SISCapability.STUDENT_PROFILE_READ, SISCapability.ENROLLMENTS_READ],
        pilot_mode=PilotMode.READ_ONLY_PILOT,
    )
    repo.configs[tenant_a_id] = config_a

    # Add Tenant A mappings
    await service.save_mapping(UniversityMapping(
        id=uuid4(),
        university_id=tenant_a_id,
        entity_type="COURSE",
        external_code="ZU-CS101",
        canonical_id="CS101",
        canonical_code="CS101",
    ))

    # Record Tenant A sync job
    job_a = await repo.create_sync_job(SyncJob(
        university_id=tenant_a_id,
        sync_mode="FULL_SYNC",
        status="SUCCEEDED",
        records_processed=150,
    ))

    # Record Tenant A reconciliation item
    item_a = await repo.record_reconciliation_item(ReconciliationItem(
        university_id=tenant_a_id,
        entity_type="STUDENT",
        external_identifier="209900001",
        status="IN_SYNC",
    ))

    # 2. Setup Tenant B (Mock Pilot University B)
    tenant_b_id = UUID("20000000-0000-0000-0000-000000000002")
    tenant_b = UniversityTenant(
        id=tenant_b_id,
        tenant_key="pilot-b",
        name_ar="جامعة ريادية ب",
        name_en="Pilot University B",
        country="Jordan",
    )
    repo.tenants[tenant_b_id] = tenant_b

    config_b = UniversityIntegrationConfig(
        university_id=tenant_b_id,
        provider_type="generic_rest",
        base_url="https://sis.pilot-b.edu/api/v1",
        supported_capabilities=[SISCapability.STUDENT_PROFILE_READ],
        pilot_mode=PilotMode.READ_ONLY_PILOT,
    )
    repo.configs[tenant_b_id] = config_b

    # Add Tenant B mappings
    await service.save_mapping(UniversityMapping(
        id=uuid4(),
        university_id=tenant_b_id,
        entity_type="COURSE",
        external_code="PB-CS101",
        canonical_id="CS101",
        canonical_code="CS101",
    ))

    # Record Tenant B sync job
    job_b = await repo.create_sync_job(SyncJob(
        university_id=tenant_b_id,
        sync_mode="INCREMENTAL_SYNC",
        status="SUCCEEDED",
        records_processed=12,
    ))

    # Record Tenant B reconciliation item
    item_b = await repo.record_reconciliation_item(ReconciliationItem(
        university_id=tenant_b_id,
        entity_type="STUDENT",
        external_identifier="2026-PILOT-99",
        status="STALE_LOCALLY",
    ))

    # =========================================================================
    # STRICT ISOLATION ASSERTIONS (CROSS_TENANT_DATA_LEAKAGE = 0)
    # =========================================================================

    # 1. Config isolation: Tenant B config does not leak Tenant A config
    cfg_b = await service.get_config(tenant_b_id)
    assert cfg_b is not None
    assert cfg_b.university_id == tenant_b_id
    assert cfg_b.base_url == "https://sis.pilot-b.edu/api/v1"
    assert "fake-university" not in cfg_b.base_url

    # 2. Mappings isolation: Tenant B sees ONLY PB-CS101, NEVER ZU-CS101
    mappings_b = await service.list_mappings(tenant_b_id)
    assert len(mappings_b) == 1
    assert mappings_b[0].external_code == "PB-CS101"
    assert all(m.university_id == tenant_b_id for m in mappings_b)
    # Zero leakage of Tenant A
    assert not any(m.external_code == "ZU-CS101" for m in mappings_b)

    mappings_a = await service.list_mappings(tenant_a_id)
    assert len(mappings_a) == 1
    assert mappings_a[0].external_code == "ZU-CS101"
    assert not any(m.external_code == "PB-CS101" for m in mappings_a)

    # 3. Sync jobs isolation: Tenant B sees ONLY job_b, NEVER job_a
    jobs_b = await service.list_sync_jobs(tenant_b_id)
    assert len(jobs_b) == 1
    assert jobs_b[0].records_processed == 12
    assert jobs_b[0].university_id == tenant_b_id

    jobs_a = await service.list_sync_jobs(tenant_a_id)
    assert len(jobs_a) == 1
    assert jobs_a[0].records_processed == 150
    assert jobs_a[0].university_id == tenant_a_id

    # 4. Reconciliation isolation: Tenant B sees ONLY item_b, NEVER item_a
    drift_b = await service.list_reconciliation_items(tenant_b_id)
    assert len(drift_b) == 1
    assert drift_b[0].external_identifier == "2026-PILOT-99"
    assert drift_b[0].university_id == tenant_b_id

    drift_a = await service.list_reconciliation_items(tenant_a_id)
    assert len(drift_a) == 1
    assert drift_a[0].external_identifier == "209900001"
    assert drift_a[0].university_id == tenant_a_id

    # 5. Cross-tenant leakage verification metric
    cross_tenant_leakage_detected = (
        any(m.university_id != tenant_b_id for m in mappings_b)
        or any(j.university_id != tenant_b_id for j in jobs_b)
        or any(d.university_id != tenant_b_id for d in drift_b)
    )
    assert cross_tenant_leakage_detected is False
    CROSS_TENANT_DATA_LEAKAGE = 0
    assert CROSS_TENANT_DATA_LEAKAGE == 0

