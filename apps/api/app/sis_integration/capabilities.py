"""Typed SIS capabilities, pilot modes, and negotiation contracts."""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class SISCapability(str, Enum):
    # Core Student & Auth
    IDENTITY_AUTH = "IDENTITY_AUTH"
    STUDENT_PROFILE_READ = "STUDENT_PROFILE_READ"
    GRADES_READ = "GRADES_READ"
    TRANSCRIPT_READ = "TRANSCRIPT_READ"
    ENROLLMENTS_READ = "ENROLLMENTS_READ"

    # Catalog & Curriculum
    CATALOG_READ = "CATALOG_READ"
    CURRICULUM_READ = "CURRICULUM_READ"
    ACADEMIC_CALENDAR_READ = "ACADEMIC_CALENDAR_READ"

    # Offerings & Timetable
    OFFERINGS_READ = "OFFERINGS_READ"
    SECTIONS_READ = "SECTIONS_READ"
    TIMETABLE = "TIMETABLE"
    SCHEDULES_READ = "SCHEDULES_READ"
    CLASSROOMS_READ = "CLASSROOMS_READ"
    INSTRUCTORS_READ = "INSTRUCTORS_READ"
    SECTION_CAPACITY = "SECTION_CAPACITY"
    SEAT_AVAILABILITY_READ = "SEAT_AVAILABILITY_READ"

    # Registration & Mutations
    REGISTRATION_READ = "REGISTRATION_READ"
    REGISTRATION_PREVIEW = "REGISTRATION_PREVIEW"
    REGISTRATION_WRITE = "REGISTRATION_WRITE"
    DROP_WRITE = "DROP_WRITE"
    REGISTRATION_DROP = "REGISTRATION_DROP"

    # Policies & Governance
    POLICIES_READ = "POLICIES_READ"
    ADVISOR_ASSIGNMENTS = "ADVISOR_ASSIGNMENTS"

    # Integration Infrastructure
    WEBHOOKS = "WEBHOOKS"
    INCREMENTAL_SYNC = "INCREMENTAL_SYNC"
    SSO = "SSO"


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
            if (
                SISCapability.DROP_WRITE not in capabilities
                and SISCapability.REGISTRATION_DROP not in capabilities
            ):
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

        if action in {"view_classrooms", "classrooms"}:
            if SISCapability.CLASSROOMS_READ not in capabilities:
                return False, "CAPABILITY_CLASSROOMS_READ_REQUIRED"
            return True, None

        return True, None

    @staticmethod
    def evaluate_feature_degradation(
        declared_capabilities: set[SISCapability],
    ) -> dict[str, dict[str, Any]]:
        """Report features that are active vs degraded or disabled."""
        return {
            "registration": {
                "available": (
                    SISCapability.REGISTRATION_WRITE in declared_capabilities
                    or SISCapability.REGISTRATION_PREVIEW in declared_capabilities
                ),
                "can_write": SISCapability.REGISTRATION_WRITE in declared_capabilities,
                "can_preview": SISCapability.REGISTRATION_PREVIEW in declared_capabilities,
                "degradation_mode": (
                    "FULL_MUTATION"
                    if SISCapability.REGISTRATION_WRITE in declared_capabilities
                    else (
                        "PREVIEW_ONLY"
                        if SISCapability.REGISTRATION_PREVIEW in declared_capabilities
                        else "ADVISORY_READ_ONLY"
                    )
                ),
            },
            "offerings_discovery": {
                "available": (
                    SISCapability.OFFERINGS_READ in declared_capabilities
                    or SISCapability.CURRICULUM_READ in declared_capabilities
                ),
                "has_sections": (
                    SISCapability.SECTIONS_READ in declared_capabilities
                    or SISCapability.OFFERINGS_READ in declared_capabilities
                ),
                "has_capacity": (
                    SISCapability.SECTION_CAPACITY in declared_capabilities
                    or SISCapability.SEAT_AVAILABILITY_READ in declared_capabilities
                ),
                "has_classrooms": SISCapability.CLASSROOMS_READ in declared_capabilities,
            },
            "synchronization": {
                "can_incremental": SISCapability.INCREMENTAL_SYNC in declared_capabilities,
                "has_webhooks": SISCapability.WEBHOOKS in declared_capabilities,
                "fallback": "FULL_SYNC_ON_DEMAND",
            },
        }
