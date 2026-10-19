"""Morshidi SIS Integration Package.

Provides generic university tenant onboarding, SIS adapter abstractions,
capability negotiation, curriculum/identity mapping, synchronization,
webhooks, and pilot readiness evaluation.
"""

from .adapter_interface import SISAdapter
from .adapter_registry import AdapterRegistry
from .capabilities import CapabilityNegotiator, PilotMode, SISCapability, TenantStatus
from .errors import (
    CapabilityNotSupportedError,
    IdentityAlreadyLinkedError,
    IdentityAmbiguousError,
    IdentityNotFoundError,
    MappingAmbiguousError,
    MappingMissingError,
    ReconciliationConflictError,
    SISAuthFailedError,
    SISIntegrationError,
    SISProtocolError,
    SISRateLimitedError,
    SISTimeoutError,
    SISUnavailableError,
    SSRFSecurityError,
    SyncCursorInvalidError,
    SyncFailedError,
    SyncPartialError,
    TenantMismatchError,
    WebhookReplayedError,
    WebhookSignatureInvalidError,
    WriteActionNotAllowedError,
)
from .fake_university_adapter import FakeUniversityAdapter
from .generic_rest_adapter import GenericRestAdapter
from .health import IntegrationHealthEvaluator
from .mapping_layer import MappingLayer
from .models import (
    ChangeBatch,
    HealthResult,
    NormalizedAuthResult,
    NormalizedCourse,
    NormalizedEnrollment,
    NormalizedGradeAttempt,
    NormalizedOffering,
    NormalizedStudent,
    NormalizedStudyPlan,
    NormalizedTerm,
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
from .service import SISIntegrationService
from .sso_readiness import SSOClaimValidator
from .sync_orchestrator import SyncOrchestrator
from .webhook_engine import WebhookEngine

__all__ = [
    "AdapterRegistry",
    "CapabilityNegotiator",
    "CapabilityNotSupportedError",
    "ChangeBatch",
    "FakeUniversityAdapter",
    "GenericRestAdapter",
    "HealthResult",
    "IdentityAlreadyLinkedError",
    "IdentityAmbiguousError",
    "IdentityNotFoundError",
    "IntegrationHealthEvaluator",
    "MappingAmbiguousError",
    "MappingLayer",
    "MappingMissingError",
    "NormalizedAuthResult",
    "NormalizedCourse",
    "NormalizedEnrollment",
    "NormalizedGradeAttempt",
    "NormalizedOffering",
    "NormalizedStudent",
    "NormalizedStudyPlan",
    "NormalizedTerm",
    "PilotMode",
    "PilotReadinessEvaluator",
    "PilotReadinessScorecard",
    "ReconciliationConflictError",
    "ReconciliationEngine",
    "ReconciliationItem",
    "SISAdapter",
    "SISAuthFailedError",
    "SISCapability",
    "SISIntegrationError",
    "SISIntegrationService",
    "SISProtocolError",
    "SISRateLimitedError",
    "SISTimeoutError",
    "SISUnavailableError",
    "SSOClaimValidator",
    "SSRFSecurityError",
    "SyncCursorInvalidError",
    "SyncFailedError",
    "SyncJob",
    "SyncOrchestrator",
    "SyncPartialError",
    "SupabaseSISIntegrationRepository",
    "TenantMismatchError",
    "TenantStatus",
    "UniversityIntegrationConfig",
    "UniversityMapping",
    "UniversityTenant",
    "WebhookEngine",
    "WebhookReplayedError",
    "WebhookSignatureInvalidError",
    "WriteActionNotAllowedError",
    "mask_secret_status",
    "resolve_secret",
    "validate_target_url",
]

