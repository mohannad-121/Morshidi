"""Integration API routes tests for institutional integrations management and inbound webhooks."""

from __future__ import annotations

import hashlib
import hmac
import time
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from app.api.routes.institutional_integrations import _service
from app.core.auth import CurrentUser, get_current_user
from app.main import app
from app.sis_integration.capabilities import PilotMode, SISCapability
from app.sis_integration.errors import SISIntegrationError, WebhookSignatureInvalidError
from app.sis_integration.models import (
    HealthResult,
    PilotReadinessScorecard,
    ReconciliationItem,
    SyncJob,
    UniversityIntegrationConfig,
    UniversityMapping,
    UniversityTenant,
)

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_UNI_ID = UUID("10000000-0000-0000-0000-000000000001")


class MockSISIntegrationService:
    """Mock service handling API route requests deterministically."""

    def __init__(self) -> None:
        self.tenant = UniversityTenant(
            id=TEST_UNI_ID,
            tenant_key="zarqa",
            name_ar="جامعة الزرقاء",
            name_en="Zarqa University",
            country="Jordan",
        )
        self.config = UniversityIntegrationConfig(
            university_id=TEST_UNI_ID,
            provider_type="fake_university",
            base_url="https://fake-university-aqdn.onrender.com",
            pilot_mode=PilotMode.READ_ONLY_PILOT,
            supported_capabilities=[SISCapability.STUDENT_PROFILE_READ],
        )

    async def list_tenants(self) -> list[UniversityTenant]:
        return [self.tenant]

    async def get_tenant_by_id(self, university_id: UUID) -> UniversityTenant:
        return self.tenant

    async def get_config(self, university_id: UUID) -> UniversityIntegrationConfig | None:
        return self.config

    async def save_config(self, config: UniversityIntegrationConfig, actor_user_id: UUID | None = None) -> UniversityIntegrationConfig:
        self.config = config
        return config

    async def get_health(self, university_id: UUID) -> HealthResult:
        return HealthResult(status="HEALTHY", connectivity=True, latency_ms=45.2)

    async def get_readiness_scorecard(self, university_id: UUID) -> PilotReadinessScorecard:
        return PilotReadinessScorecard(
            university_id=str(TEST_UNI_ID),
            tenant_key="zarqa",
            overall_status="PASS",
            checklist={"TENANT_CONFIG_EXISTS": "PASS", "CONNECTIVITY_PROBE": "PASS"},
            mapping_coverage={"overall": 100.0},
            summary_ar="جاهز للإطلاق التجريبي",
        )

    async def list_mappings(self, university_id: UUID, entity_type: str | None = None) -> list[UniversityMapping]:
        return [
            UniversityMapping(
                id=uuid4(),
                university_id=TEST_UNI_ID,
                entity_type="COURSE",
                external_code="CS101",
                canonical_id="CS101",
                canonical_code="CS101",
            )
        ]

    async def save_mapping(self, mapping: UniversityMapping, actor_user_id: UUID | None = None) -> UniversityMapping:
        mapping.id = uuid4()
        return mapping

    async def delete_mapping(self, university_id: UUID, mapping_id: UUID, actor_user_id: UUID | None = None) -> bool:
        return True

    async def trigger_sync(self, university_id: UUID, mode: str = "FULL_SYNC", cursor: str | None = None, actor_user_id: UUID | None = None) -> SyncJob:
        return SyncJob(
            id=uuid4(),
            university_id=TEST_UNI_ID,
            sync_mode=mode,  # type: ignore[arg-type]
            status="SUCCEEDED",
            records_processed=25,
        )

    async def list_sync_jobs(self, university_id: UUID, limit: int = 20) -> list[SyncJob]:
        return [
            SyncJob(
                id=uuid4(),
                university_id=TEST_UNI_ID,
                sync_mode="FULL_SYNC",
                status="SUCCEEDED",
                records_processed=25,
            )
        ]

    async def list_reconciliation_items(self, university_id: UUID, status: str | None = None) -> list[ReconciliationItem]:
        return [
            ReconciliationItem(
                id=uuid4(),
                university_id=TEST_UNI_ID,
                entity_type="STUDENT",
                external_identifier="209900001",
                status="IN_SYNC",
            )
        ]

    async def handle_inbound_webhook(self, tenant_key: str, provider: str, raw_body: bytes, headers: dict[str, str]) -> dict[str, Any]:
        sig = headers.get("x-morshidi-signature")
        if not sig or "invalid" in sig:
            raise WebhookSignatureInvalidError("Invalid signature")
        return {"status": "ACCEPTED", "event_id": headers.get("x-morshidi-event-id")}


def test_institutional_integrations_routes():
    """Verify all institutional integration API routes respond correctly and with private, no-store."""
    mock_service = MockSISIntegrationService()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(TEST_USER_ID)
    app.dependency_overrides[_service] = lambda: mock_service

    try:
        with TestClient(app) as client:
            # 1. Tenants
            res = client.get("/api/v1/institutional/integrations/tenants")
            assert res.status_code == 200
            assert res.headers["cache-control"] == "private, no-store"
            data = res.json()
            assert len(data) == 1
            assert data[0]["tenant_key"] == "zarqa"

            # 2. Config
            res = client.get(f"/api/v1/institutional/integrations/config?university_id={TEST_UNI_ID}")
            assert res.status_code == 200
            assert res.json()["provider_type"] == "fake_university"

            # 3. Health
            res = client.get(f"/api/v1/institutional/integrations/health?university_id={TEST_UNI_ID}")
            assert res.status_code == 200
            assert res.json()["status"] == "HEALTHY"

            # 4. Readiness
            res = client.get(f"/api/v1/institutional/integrations/readiness?university_id={TEST_UNI_ID}")
            assert res.status_code == 200
            assert res.json()["overall_status"] == "PASS"

            # 5. Mappings
            res = client.get(f"/api/v1/institutional/integrations/mappings?university_id={TEST_UNI_ID}")
            assert res.status_code == 200
            assert len(res.json()) == 1

            # 6. Trigger sync
            res = client.post("/api/v1/institutional/integrations/sync", json={"university_id": str(TEST_UNI_ID), "mode": "FULL_SYNC"})
            assert res.status_code == 200
            assert res.json()["status"] == "SUCCEEDED"

            # 7. Sync jobs
            res = client.get(f"/api/v1/institutional/integrations/sync/jobs?university_id={TEST_UNI_ID}")
            assert res.status_code == 200
            assert len(res.json()) == 1

            # 8. Reconciliation
            res = client.get(f"/api/v1/institutional/integrations/reconciliation?university_id={TEST_UNI_ID}")
            assert res.status_code == 200
            assert len(res.json()) == 1
            assert res.json()[0]["status"] == "IN_SYNC"

    finally:
        app.dependency_overrides.clear()


def test_inbound_webhook_route():
    """Verify inbound webhook endpoint verifies signature and responds properly."""
    mock_service = MockSISIntegrationService()
    app.dependency_overrides[_service] = lambda: mock_service

    try:
        with TestClient(app) as client:
            now_ts = str(int(time.time()))

            # 1. Valid webhook
            res = client.post(
                "/api/v1/integrations/zarqa/webhooks/generic",
                content=b'{"event":"TEST"}',
                headers={
                    "x-morshidi-signature": "sha256=validsig123",
                    "x-morshidi-timestamp": now_ts,
                    "x-morshidi-event-id": "evt-77",
                },
            )
            assert res.status_code == 200
            assert res.json()["status"] == "ACCEPTED"

            # 2. Invalid signature returns 401
            res_bad = client.post(
                "/api/v1/integrations/zarqa/webhooks/generic",
                content=b'{"event":"TEST"}',
                headers={
                    "x-morshidi-signature": "sha256=invalid-signature",
                    "x-morshidi-timestamp": now_ts,
                },
            )
            assert res_bad.status_code == 401
    finally:
        app.dependency_overrides.clear()

