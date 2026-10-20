"""API routes for institutional pilot onboarding, requirements, blockers, acceptance, and reports."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, get_current_user
from app.pilot_onboarding.models import (
    AcceptanceStatus,
    BlockerSeverity,
    BlockerStatus,
    DiscoveryIntake,
    PilotAcceptanceCheck,
    PilotActivity,
    PilotBlocker,
    PilotCohortScope,
    PilotMode,
    PilotReport,
    PilotRequirement,
    PilotSignoff,
    PilotStakeholder,
    PilotStatus,
    PilotSummary,
    RequirementStatus,
    SignoffRole,
    SignoffStatus,
    StakeholderRole,
    UniversityPilot,
)
from app.pilot_onboarding.service import PilotService, PilotServiceError, PilotTransitionError
from app.pilot_onboarding.write_enablement import WriteEnablementResult

router = APIRouter(
    prefix="/api/v1/institutional/pilots",
    tags=["institutional-pilots"],
    dependencies=[Depends(get_current_user)],
)
User = Annotated[CurrentUser, Depends(get_current_user)]


def _service(request: Request) -> PilotService:
    service = getattr(request.app.state, "pilot_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pilot onboarding service is unavailable",
        )
    return service


Service = Annotated[PilotService, Depends(_service)]


def _parse_actor(user: CurrentUser) -> tuple[UUID | None, str]:
    """Safely extracts UUID actor_id and email from CurrentUser."""
    raw_id = getattr(user, "user_id", None) or getattr(user, "id", None)
    actor_id: UUID | None = None
    if raw_id:
        try:
            actor_id = UUID(str(raw_id))
        except Exception:
            actor_id = None
    actor_email = getattr(user, "email", None) or (f"{raw_id}@morshidi.institution" if raw_id else "system")
    return actor_id, actor_email


# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------


class CreatePilotRequest(BaseModel):
    university_id: UUID
    pilot_name: str = Field(..., min_length=2)
    mode: PilotMode = PilotMode.READ_ONLY_PILOT
    target_start_date: date | None = None
    target_end_date: date | None = None
    cohort_scope: PilotCohortScope = Field(default_factory=PilotCohortScope)
    discovery_intake: DiscoveryIntake = Field(default_factory=DiscoveryIntake)
    notes: str = ""


class UpdatePilotRequest(BaseModel):
    pilot_name: str | None = None
    mode: PilotMode | None = None
    target_start_date: date | None = None
    target_end_date: date | None = None
    cohort_scope: dict[str, Any] | None = None
    discovery_intake: dict[str, Any] | None = None
    technical_questionnaire: dict[str, Any] | None = None
    security_questionnaire: dict[str, Any] | None = None
    notes: str | None = None


class TransitionRequest(BaseModel):
    target_status: PilotStatus
    notes: str = ""


class UpdateRequirementRequest(BaseModel):
    status: RequirementStatus
    secret_ref_name: str | None = None
    notes: str = ""
    validated_by: str | None = None


class CreateBlockerRequest(BaseModel):
    blocker_code: str
    title_ar: str
    severity: BlockerSeverity = BlockerSeverity.SEV2
    owner_role: str = "UNIVERSITY_TECHNICAL_CONTACT"
    resolution_notes: str = ""


class UpdateBlockerRequest(BaseModel):
    status: BlockerStatus
    resolution_notes: str = ""


class CreateStakeholderRequest(BaseModel):
    role: StakeholderRole
    name: str
    title: str = ""
    email: str
    phone: str = ""
    notes: str = ""


class UpdateAcceptanceCheckRequest(BaseModel):
    status: AcceptanceStatus
    evidence_ref: str = ""
    notes: str = ""


class RecordSignoffRequest(BaseModel):
    signoff_role: SignoffRole
    signee_name: str
    signee_role: str
    status: SignoffStatus = SignoffStatus.APPROVED
    decision_notes: str = ""


# ---------------------------------------------------------------------------
# Pilot Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[UniversityPilot])
async def list_pilots(
    user: User,
    service: Service,
    response: Response,
    university_id: UUID | None = Query(None),
) -> list[UniversityPilot]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_pilots(university_id)


@router.post("", response_model=UniversityPilot, status_code=status.HTTP_201_CREATED)
async def create_pilot(
    user: User,
    service: Service,
    req: CreatePilotRequest,
) -> UniversityPilot:
    pilot = UniversityPilot(
        university_id=req.university_id,
        pilot_name=req.pilot_name,
        mode=req.mode,
        target_start_date=req.target_start_date,
        target_end_date=req.target_end_date,
        cohort_scope=req.cohort_scope,
        discovery_intake=req.discovery_intake,
        notes=req.notes,
    )
    actor_id, actor_email = _parse_actor(user)
    try:
        return await service.create_pilot(
            pilot,
            actor_id=actor_id,
            actor_email=actor_email,
        )
    except Exception as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("/{pilot_id}", response_model=UniversityPilot)
async def get_pilot(
    pilot_id: UUID,
    user: User,
    service: Service,
    response: Response,
) -> UniversityPilot:
    response.headers["Cache-Control"] = "private, no-store"
    pilot = await service.get_pilot(pilot_id)
    if not pilot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pilot not found")
    return pilot


@router.patch("/{pilot_id}", response_model=UniversityPilot)
async def update_pilot(
    pilot_id: UUID,
    user: User,
    service: Service,
    req: UpdatePilotRequest,
) -> UniversityPilot:
    updates = {k: v for k, v in req.model_dump(exclude_unset=True).items() if v is not None}
    actor_id, actor_email = _parse_actor(user)
    try:
        return await service.update_pilot(
            pilot_id,
            updates,
            actor_id=actor_id,
            actor_email=actor_email,
        )
    except PilotServiceError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


@router.get("/{pilot_id}/summary", response_model=PilotSummary)
async def get_pilot_summary(
    pilot_id: UUID,
    user: User,
    service: Service,
    response: Response,
) -> PilotSummary:
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return await service.get_pilot_summary(pilot_id)
    except PilotServiceError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.post("/{pilot_id}/transition", response_model=UniversityPilot)
async def transition_pilot(
    pilot_id: UUID,
    user: User,
    service: Service,
    req: TransitionRequest,
) -> UniversityPilot:
    actor_id, actor_email = _parse_actor(user)
    try:
        return await service.transition_pilot(
            pilot_id,
            req.target_status,
            actor_id=actor_id,
            actor_email=actor_email,
            notes=req.notes,
        )
    except PilotTransitionError as err:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(err)) from err
    except PilotServiceError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)) from err


# ---------------------------------------------------------------------------
# Requirements Endpoints
# ---------------------------------------------------------------------------


@router.get("/{pilot_id}/requirements", response_model=list[PilotRequirement])
async def list_requirements(
    pilot_id: UUID,
    user: User,
    service: Service,
    response: Response,
) -> list[PilotRequirement]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_requirements(pilot_id)


@router.patch("/{pilot_id}/requirements/{requirement_key}", response_model=PilotRequirement)
async def update_requirement(
    pilot_id: UUID,
    requirement_key: str,
    user: User,
    service: Service,
    req: UpdateRequirementRequest,
) -> PilotRequirement:
    actor_id, actor_email = _parse_actor(user)
    try:
        return await service.update_requirement_status(
            pilot_id,
            requirement_key,
            req.status,
            secret_ref_name=req.secret_ref_name,
            notes=req.notes,
            validated_by=req.validated_by or actor_email,
            actor_id=actor_id,
            actor_email=actor_email,
        )
    except PilotServiceError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


# ---------------------------------------------------------------------------
# Blockers Endpoints
# ---------------------------------------------------------------------------


@router.get("/{pilot_id}/blockers", response_model=list[PilotBlocker])
async def list_blockers(
    pilot_id: UUID,
    user: User,
    service: Service,
    response: Response,
) -> list[PilotBlocker]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_blockers(pilot_id)


@router.post("/{pilot_id}/blockers", response_model=PilotBlocker, status_code=status.HTTP_201_CREATED)
async def create_blocker(
    pilot_id: UUID,
    user: User,
    service: Service,
    req: CreateBlockerRequest,
) -> PilotBlocker:
    actor_id, actor_email = _parse_actor(user)
    blocker = PilotBlocker(
        pilot_id=pilot_id,
        blocker_code=req.blocker_code,
        title_ar=req.title_ar,
        severity=req.severity,
        owner_role=req.owner_role,
        resolution_notes=req.resolution_notes,
    )
    return await service.add_blocker(
        blocker,
        actor_id=actor_id,
        actor_email=actor_email,
    )


@router.patch("/{pilot_id}/blockers/{blocker_id}", response_model=PilotBlocker)
async def update_blocker(
    pilot_id: UUID,
    blocker_id: UUID,
    user: User,
    service: Service,
    req: UpdateBlockerRequest,
) -> PilotBlocker:
    actor_id, actor_email = _parse_actor(user)
    try:
        return await service.update_blocker(
            pilot_id,
            blocker_id,
            req.status,
            resolution_notes=req.resolution_notes,
            actor_id=actor_id,
            actor_email=actor_email,
        )
    except PilotServiceError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


# ---------------------------------------------------------------------------
# Stakeholders Endpoints
# ---------------------------------------------------------------------------


@router.get("/{pilot_id}/stakeholders", response_model=list[PilotStakeholder])
async def list_stakeholders(
    pilot_id: UUID,
    user: User,
    service: Service,
    response: Response,
) -> list[PilotStakeholder]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_stakeholders(pilot_id)


@router.post("/{pilot_id}/stakeholders", response_model=PilotStakeholder, status_code=status.HTTP_201_CREATED)
async def add_stakeholder(
    pilot_id: UUID,
    user: User,
    service: Service,
    req: CreateStakeholderRequest,
) -> PilotStakeholder:
    stakeholder = PilotStakeholder(
        pilot_id=pilot_id,
        role=req.role,
        name=req.name,
        title=req.title,
        email=req.email,
        phone=req.phone,
        notes=req.notes,
    )
    actor_id, actor_email = _parse_actor(user)
    return await service.add_stakeholder(
        stakeholder,
        actor_id=actor_id,
        actor_email=actor_email,
    )


@router.delete("/{pilot_id}/stakeholders/{stakeholder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stakeholder(
    pilot_id: UUID,
    stakeholder_id: UUID,
    user: User,
    service: Service,
) -> None:
    actor_id, actor_email = _parse_actor(user)
    await service.remove_stakeholder(
        pilot_id,
        stakeholder_id,
        actor_id=actor_id,
        actor_email=actor_email,
    )


# ---------------------------------------------------------------------------
# Acceptance Checks Endpoints
# ---------------------------------------------------------------------------


@router.get("/{pilot_id}/acceptance", response_model=list[PilotAcceptanceCheck])
async def list_acceptance_checks(
    pilot_id: UUID,
    user: User,
    service: Service,
    response: Response,
) -> list[PilotAcceptanceCheck]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_acceptance_checks(pilot_id)


@router.post("/{pilot_id}/acceptance/run", response_model=list[PilotAcceptanceCheck])
async def run_automated_acceptance(
    pilot_id: UUID,
    user: User,
    service: Service,
) -> list[PilotAcceptanceCheck]:
    actor_id, actor_email = _parse_actor(user)
    try:
        return await service.evaluate_automated_acceptance_checks(
            pilot_id,
            actor_id=actor_id,
            actor_email=actor_email,
        )
    except PilotServiceError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.patch("/{pilot_id}/acceptance/{check_key}", response_model=PilotAcceptanceCheck)
async def update_acceptance_check(
    pilot_id: UUID,
    check_key: str,
    user: User,
    service: Service,
    req: UpdateAcceptanceCheckRequest,
) -> PilotAcceptanceCheck:
    actor_id, actor_email = _parse_actor(user)
    try:
        return await service.update_acceptance_check(
            pilot_id,
            check_key,
            req.status,
            evidence_ref=req.evidence_ref,
            tested_by=actor_email or "ADMIN",
            notes=req.notes,
            actor_id=actor_id,
            actor_email=actor_email,
        )
    except PilotServiceError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


# ---------------------------------------------------------------------------
# Sign-offs Endpoints
# ---------------------------------------------------------------------------


@router.get("/{pilot_id}/signoffs", response_model=list[PilotSignoff])
async def list_signoffs(
    pilot_id: UUID,
    user: User,
    service: Service,
    response: Response,
) -> list[PilotSignoff]:
    response.headers["Cache-Control"] = "private, no-store"
    return await service.list_signoffs(pilot_id)


@router.post("/{pilot_id}/signoffs", response_model=PilotSignoff)
async def record_signoff(
    pilot_id: UUID,
    user: User,
    service: Service,
    req: RecordSignoffRequest,
) -> PilotSignoff:
    actor_id, actor_email = _parse_actor(user)
    signoff = PilotSignoff(
        pilot_id=pilot_id,
        signoff_role=req.signoff_role,
        signee_name=req.signee_name,
        signee_role=req.signee_role,
        status=req.status,
        decision_notes=req.decision_notes,
    )
    return await service.record_signoff(
        signoff,
        actor_id=actor_id,
        actor_email=actor_email,
    )


# ---------------------------------------------------------------------------
# Write Enablement Review & Acceptance Report
# ---------------------------------------------------------------------------


@router.get("/{pilot_id}/write-enablement", response_model=WriteEnablementResult)
async def evaluate_write_enablement(
    pilot_id: UUID,
    user: User,
    service: Service,
    response: Response,
) -> WriteEnablementResult:
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return await service.evaluate_write_enablement(pilot_id)
    except PilotServiceError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.get("/{pilot_id}/report", response_model=PilotReport)
async def get_acceptance_report(
    pilot_id: UUID,
    user: User,
    service: Service,
    response: Response,
) -> PilotReport:
    response.headers["Cache-Control"] = "private, no-store"
    try:
        return await service.generate_acceptance_report(pilot_id)
    except PilotServiceError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err)) from err


@router.get("/{pilot_id}/activity", response_model=list[PilotActivity])
async def list_activity(
    pilot_id: UUID,
    user: User,
    service: Service,
    response: Response,
) -> list[PilotActivity]:
    response.headers["Cache-Control"] = "private, no-store"
    pilot = await service.get_pilot(pilot_id)
    if not pilot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pilot not found")
    return await service._repo.list_activity(pilot_id)
