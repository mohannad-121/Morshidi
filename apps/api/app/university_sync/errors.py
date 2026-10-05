"""Domain exceptions and error codes for university integration."""

from __future__ import annotations

from enum import Enum


class UniversityErrorCode(str, Enum):
    INVALID_UNIVERSITY_CREDENTIALS = "INVALID_UNIVERSITY_CREDENTIALS"
    UNIVERSITY_RATE_LIMITED = "UNIVERSITY_RATE_LIMITED"
    UNIVERSITY_UNAVAILABLE = "UNIVERSITY_UNAVAILABLE"
    UNIVERSITY_PROTOCOL_ERROR = "UNIVERSITY_PROTOCOL_ERROR"
    UNIVERSITY_IDENTITY_CONFLICT = "UNIVERSITY_IDENTITY_CONFLICT"
    UNIVERSITY_PLAN_NOT_MAPPED = "UNIVERSITY_PLAN_NOT_MAPPED"
    UNIVERSITY_COURSE_NOT_MAPPED = "UNIVERSITY_COURSE_NOT_MAPPED"
    UNIVERSITY_SYNC_FAILED = "UNIVERSITY_SYNC_FAILED"
    INTERNAL_IDENTITY_PROVISION_FAILED = "INTERNAL_IDENTITY_PROVISION_FAILED"


class UniversitySyncError(Exception):
    """Base exception for university integration errors."""

    def __init__(self, code: UniversityErrorCode, message: str = "") -> None:
        self.code = code
        self.message = message or code.value
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code.value!r}, message={self.message!r})"


class InvalidUniversityCredentialsError(UniversitySyncError):
    def __init__(self, message: str = "Invalid university credentials or expired integration token") -> None:
        super().__init__(UniversityErrorCode.INVALID_UNIVERSITY_CREDENTIALS, message)


class UniversityRateLimitedError(UniversitySyncError):
    def __init__(self, message: str = "University integration request was rate limited", retry_after: int | None = None) -> None:
        super().__init__(UniversityErrorCode.UNIVERSITY_RATE_LIMITED, message)
        self.retry_after = retry_after


class UniversityUnavailableError(UniversitySyncError):
    def __init__(self, message: str = "University service is unavailable") -> None:
        super().__init__(UniversityErrorCode.UNIVERSITY_UNAVAILABLE, message)


class UniversityProtocolError(UniversitySyncError):
    def __init__(self, message: str = "University integration returned invalid or malformed data") -> None:
        super().__init__(UniversityErrorCode.UNIVERSITY_PROTOCOL_ERROR, message)


class UniversityIdentityConflictError(UniversitySyncError):
    def __init__(self, message: str = "University identity mapping conflict") -> None:
        super().__init__(UniversityErrorCode.UNIVERSITY_IDENTITY_CONFLICT, message)


class UniversityPlanNotMappedError(UniversitySyncError):
    def __init__(self, message: str = "University study plan could not be mapped to catalog") -> None:
        super().__init__(UniversityErrorCode.UNIVERSITY_PLAN_NOT_MAPPED, message)


class UniversityCourseNotMappedError(UniversitySyncError):
    def __init__(self, message: str = "University course could not be mapped to catalog") -> None:
        super().__init__(UniversityErrorCode.UNIVERSITY_COURSE_NOT_MAPPED, message)


class UniversitySyncFailedError(UniversitySyncError):
    def __init__(self, message: str = "University synchronization failed") -> None:
        super().__init__(UniversityErrorCode.UNIVERSITY_SYNC_FAILED, message)


class InternalIdentityProvisionFailedError(UniversitySyncError):
    def __init__(self, message: str = "Internal Morshidi shadow identity provisioning failed") -> None:
        super().__init__(UniversityErrorCode.INTERNAL_IDENTITY_PROVISION_FAILED, message)
