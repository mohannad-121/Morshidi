"""API routes for institutional SIS integration management, readiness, and webhooks."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, get_current_user
from app.sis_integration.errors import (
    SISIntegrationError,
    WebhookReplayedError,
    WebhookSignatureInvalidError,
)
from app.sis_integration.models import (
    HealthResult,
    PilotReadinessScorecard,
    ReconciliationItem,
    SyncJob,
    UniversityIntegrationConfig,
    UniversityMapping,
    UniversityTenant,
)
from app.sis_integration.service import SISIntegrationService

router = APIRouter(
    prefix="/api/v1/institutional/integrations",
    tags=["institutional-integrations"],
    dependencies=[Depends(get_current_user)],
)
User = Annotated[CurrentUser, Depends(get_current_user)]


def _service(request: Request) -> SISIntegrationService:
    service = getattr(request.app.state, "sis_integration_service", None)
    if service is None:
        raise SISIntegrationError(
            "INTEGRATION_SERVICE_UNAVAILABLE",
            "SIS Integration service is unavailable",
            status_code=503,
        )
    return service


Service = Annotated[SISIntegrationService, Depends(_service)]


# --- Tenant Endpoints ---

@router.get("/tenants", response_model=list[UniversityTenant])
async def list_tenants(
    user: User, service: Service, response: Response,
) -> list[UniversityTenant]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_tenants()


@router.get("/tenants/{university_id}", response_model=UniversityTenant)
async def get_tenant(
    university_id: UUID, user: User, service: Service, response: Response,
) -> UniversityTenant:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.get_tenant_by_id(university_id)


# --- Configuration Endpoints ---

@router.get("/config", response_model=UniversityIntegrationConfig | None)
async def get_config(
    university_id: Annotated[UUID, Query()],
    user: User,
    service: Service,
    response: Response,
) -> UniversityIntegrationConfig | None:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.get_config(university_id)


@router.post("/config", response_model=UniversityIntegrationConfig)
async def save_config(
    config: UniversityIntegrationConfig,
    user: User,
    service: Service,
    response: Response,
) -> UniversityIntegrationConfig:
    response.headers["Cache-Control"] = "private, no-store"
    actor_id = UUID(user.user_id) if user.user_id else None
    return await service.save_config(config, actor_user_id=actor_id)


# --- Health & Readiness Endpoints ---

@router.get("/health", response_model=HealthResult)
async def get_health(
    university_id: Annotated[UUID, Query()],
    user: User,
    service: Service,
    response: Response,
) -> HealthResult:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.get_health(university_id)


@router.get("/readiness", response_model=PilotReadinessScorecard)
async def get_readiness_scorecard(
    university_id: Annotated[UUID, Query()],
    user: User,
    service: Service,
    response: Response,
) -> PilotReadinessScorecard:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.get_readiness_scorecard(university_id)


# --- Mapping Endpoints ---

@router.get("/mappings", response_model=list[UniversityMapping])
async def list_mappings(
    university_id: Annotated[UUID, Query()],
    user: User,
    service: Service,
    response: Response,
    entity_type: Annotated[str | None, Query()] = None,
) -> list[UniversityMapping]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_mappings(university_id, entity_type)


@router.post("/mappings", response_model=UniversityMapping)
async def save_mapping(
    mapping: UniversityMapping,
    user: User,
    service: Service,
    response: Response,
) -> UniversityMapping:
    response.headers["Cache-Control"] = "private, no-store"
    actor_id = UUID(user.user_id) if user.user_id else None
    return await service.save_mapping(mapping, actor_user_id=actor_id)


class BulkMappingsRequest(BaseModel):
    university_id: UUID
    mappings: list[UniversityMapping]


@router.post("/mappings/bulk")
async def bulk_save_mappings(
    req: BulkMappingsRequest,
    user: User,
    service: Service,
    response: Response,
) -> dict[str, int]:
    response.headers["Cache-Control"] = "private, no-store"
    count = await service.repository.bulk_upsert_mappings(req.mappings)
    return {"saved_count": count}


@router.delete("/mappings/{mapping_id}")
async def delete_mapping(
    mapping_id: UUID,
    university_id: Annotated[UUID, Query()],
    user: User,
    service: Service,
    response: Response,
) -> dict[str, bool]:
    response.headers["Cache-Control"] = "private, no-store"
    actor_id = UUID(user.user_id) if user.user_id else None
    deleted = await service.delete_mapping(university_id, mapping_id, actor_user_id=actor_id)
    return {"deleted": deleted}


# --- Synchronization Endpoints ---

class TriggerSyncRequest(BaseModel):
    university_id: UUID
    mode: str = Field(default="FULL_SYNC")
    cursor: str | None = None


@router.post("/sync", response_model=SyncJob)
async def trigger_sync(
    req: TriggerSyncRequest,
    user: User,
    service: Service,
    response: Response,
) -> SyncJob:
    response.headers["Cache-Control"] = "private, no-store"
    actor_id = UUID(user.user_id) if user.user_id else None
    return await service.trigger_sync(
        req.university_id,
        mode=req.mode,
        cursor=req.cursor,
        actor_user_id=actor_id,
    )


@router.get("/sync/jobs", response_model=list[SyncJob])
async def list_sync_jobs(
    university_id: Annotated[UUID, Query()],
    user: User,
    service: Service,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[SyncJob]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_sync_jobs(university_id, limit=limit)


# --- Reconciliation Drift Endpoints ---

@router.get("/reconciliation", response_model=list[ReconciliationItem])
async def list_reconciliation(
    university_id: Annotated[UUID, Query()],
    user: User,
    service: Service,
    response: Response,
    status: Annotated[str | None, Query()] = None,
) -> list[ReconciliationItem]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_reconciliation_items(university_id, status=status)


# --- Public / External Multi-Tenant Webhook Receiver Router ---

webhook_router = APIRouter(
    prefix="/api/v1/integrations",
    tags=["sis-webhooks"],
)


@webhook_router.post("/{tenant_key}/webhooks/{provider}")
async def receive_webhook(
    tenant_key: str,
    provider: str,
    request: Request,
    service: Service,
) -> dict[str, Any]:
    raw_body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    try:
        return await service.handle_inbound_webhook(
            tenant_key=tenant_key,
            provider=provider,
            raw_body=raw_body,
            headers=headers,
        )
    except WebhookSignatureInvalidError as err:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err.detail)
    except WebhookReplayedError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=err.detail)
    except SISIntegrationError as err:
        raise HTTPException(status_code=err.status_code, detail=err.detail)
