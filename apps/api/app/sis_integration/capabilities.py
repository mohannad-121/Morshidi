"""Typed SIS capabilities, pilot modes, and negotiation contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class SISCapability(str, Enum):
    IDENTITY_AUTH = "IDENTITY_AUTH"
    STUDENT_PROFILE_READ = "STUDENT_PROFILE_READ"
    GRADES_READ = "GRADES_READ"
    ENROLLMENTS_READ = "ENROLLMENTS_READ"
    CURRICULUM_READ = "CURRICULUM_READ"
    OFFERINGS_READ = "OFFERINGS_READ"
    REGISTRATION_PREVIEW = "REGISTRATION_PREVIEW"
    REGISTRATION_WRITE = "REGISTRATION_WRITE"
    DROP_WRITE = "DROP_WRITE"
    WEBHOOKS = "WEBHOOKS"
    INCREMENTAL_SYNC = "INCREMENTAL_SYNC"
    SSO = "SSO"
    ADVISOR_ASSIGNMENTS = "ADVISOR_ASSIGNMENTS"
    SECTION_CAPACITY = "SECTION_CAPACITY"
    TIMETABLE = "TIMETABLE"


class PilotMode(str, Enum):
    READ_ONLY_PILOT = "READ_ONLY_PILOT"
    WRITE_ENABLED_PILOT = "WRITE_ENABLED_PILOT"


class TenantStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIGURING = "CONFIGURING"
    VALIDATING = "VALIDATING"
    PILOT_READY = "PILOT_READY"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


class CapabilityNegotiator:
    """Evaluates whether an operation is permitted under tenant capabilities and pilot mode."""

    @staticmethod
    def is_action_permitted(
        action: str,
        capabilities: set[SISCapability],
        pilot_mode: PilotMode,
        tenant_status: TenantStatus,
    ) -> tuple[bool, str | None]:
        if tenant_status == TenantStatus.SUSPENDED:
            return False, "TENANT_SUSPENDED"

        # Write operations strictly require WRITE_ENABLED_PILOT and specific write capabilities
        if action in {"register", "register_sections"}:
            if pilot_mode != PilotMode.WRITE_ENABLED_PILOT:
                return False, "WRITE_ACTION_BLOCKED_BY_PILOT_MODE"
            if SISCapability.REGISTRATION_WRITE not in capabilities:
                return False, "CAPABILITY_REGISTRATION_WRITE_REQUIRED"
            return True, None

        if action in {"drop", "drop_sections"}:
            if pilot_mode != PilotMode.WRITE_ENABLED_PILOT:
                return False, "WRITE_ACTION_BLOCKED_BY_PILOT_MODE"
            if SISCapability.DROP_WRITE not in capabilities:
                return False, "CAPABILITY_DROP_WRITE_REQUIRED"
            return True, None

        if action in {"preview", "preview_registration"}:
            if SISCapability.REGISTRATION_PREVIEW not in capabilities:
                return False, "CAPABILITY_REGISTRATION_PREVIEW_REQUIRED"
            return True, None

        if action == "incremental_sync":
            if SISCapability.INCREMENTAL_SYNC not in capabilities:
                return False, "CAPABILITY_INCREMENTAL_SYNC_REQUIRED"
            return True, None

        if action == "webhooks":
            if SISCapability.WEBHOOKS not in capabilities:
                return False, "CAPABILITY_WEBHOOKS_REQUIRED"
            return True, None

        if action == "sso":
            if SISCapability.SSO not in capabilities:
                return False, "CAPABILITY_SSO_REQUIRED"
            return True, None

        return True, None

