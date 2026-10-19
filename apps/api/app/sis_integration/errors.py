"""Standardized exception hierarchy for SIS integration operations."""

from __future__ import annotations


class SISIntegrationError(Exception):
    def __init__(self, code: str, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status_code = status_code


class SISUnavailableError(SISIntegrationError):
    def __init__(self, detail: str = "External SIS is currently unavailable") -> None:
        super().__init__("SIS_UNAVAILABLE", detail, 503)


class SISTimeoutError(SISIntegrationError):
    def __init__(self, detail: str = "External SIS request timed out") -> None:
        super().__init__("SIS_TIMEOUT", detail, 504)


class SISAuthFailedError(SISIntegrationError):
    def __init__(self, detail: str = "Authentication with external SIS failed") -> None:
        super().__init__("SIS_AUTH_FAILED", detail, 401)


class SISProtocolError(SISIntegrationError):
    def __init__(self, detail: str = "External SIS returned an incompatible payload") -> None:
        super().__init__("SIS_PROTOCOL_ERROR", detail, 502)


class SISRateLimitedError(SISIntegrationError):
    def __init__(self, detail: str = "External SIS rate limit exceeded", retry_after: int | None = None) -> None:
        super().__init__("SIS_RATE_LIMITED", detail, 429)
        self.retry_after = retry_after


class IdentityNotFoundError(SISIntegrationError):
    def __init__(self, detail: str = "External student identity could not be found") -> None:
        super().__init__("IDENTITY_NOT_FOUND", detail, 404)


class IdentityAmbiguousError(SISIntegrationError):
    def __init__(self, detail: str = "External identity matches multiple candidate profiles") -> None:
        super().__init__("IDENTITY_AMBIGUOUS", detail, 409)


class IdentityAlreadyLinkedError(SISIntegrationError):
    def __init__(self, detail: str = "External identity is already linked to another profile") -> None:
        super().__init__("IDENTITY_ALREADY_LINKED", detail, 409)


class TenantMismatchError(SISIntegrationError):
    def __init__(self, detail: str = "Identity claim belongs to a different university tenant") -> None:
        super().__init__("IDENTITY_TENANT_MISMATCH", detail, 403)


class MappingMissingError(SISIntegrationError):
    def __init__(self, detail: str = "Required curriculum or entity mapping is missing") -> None:
        super().__init__("MAPPING_MISSING", detail, 409)


class MappingAmbiguousError(SISIntegrationError):
    def __init__(self, detail: str = "External code matches multiple canonical entities") -> None:
        super().__init__("MAPPING_AMBIGUOUS", detail, 409)


class SyncFailedError(SISIntegrationError):
    def __init__(self, detail: str = "Synchronization job failed") -> None:
        super().__init__("SYNC_FAILED", detail, 500)


class SyncPartialError(SISIntegrationError):
    def __init__(self, detail: str = "Synchronization job completed with partial failures") -> None:
        super().__init__("SYNC_PARTIAL", detail, 207)


class SyncCursorInvalidError(SISIntegrationError):
    def __init__(self, detail: str = "Incremental sync cursor is invalid or stale") -> None:
        super().__init__("SYNC_CURSOR_INVALID", detail, 422)


class WebhookSignatureInvalidError(SISIntegrationError):
    def __init__(self, detail: str = "Webhook signature verification failed") -> None:
        super().__init__("WEBHOOK_SIGNATURE_INVALID", detail, 401)


class WebhookReplayedError(SISIntegrationError):
    def __init__(self, detail: str = "Webhook timestamp is outside acceptable replay window") -> None:
        super().__init__("WEBHOOK_REPLAYED", detail, 400)


class ReconciliationConflictError(SISIntegrationError):
    def __init__(self, detail: str = "Reconciliation conflict detected between SIS and local shadow") -> None:
        super().__init__("RECONCILIATION_CONFLICT", detail, 409)


class CapabilityNotSupportedError(SISIntegrationError):
    def __init__(self, detail: str = "Requested capability is not supported by this university SIS") -> None:
        super().__init__("CAPABILITY_NOT_SUPPORTED", detail, 400)


class WriteActionNotAllowedError(SISIntegrationError):
    def __init__(self, detail: str = "Write operations are disabled for this tenant pilot mode") -> None:
        super().__init__("WRITE_ACTION_NOT_ALLOWED", detail, 403)


class SSRFSecurityError(SISIntegrationError):
    def __init__(self, detail: str = "Configured target URL violates SSRF security policy") -> None:
        super().__init__("SSRF_SECURITY_VIOLATION", detail, 400)

