"""Safe typed failures for student academic-state retrieval."""


class StudentRepositoryError(Exception):
    """Base class for student repository failures."""


class StudentProfileNotFound(StudentRepositoryError):
    """The owner has no persisted academic profile."""


class StudentProfileIntegrityError(StudentRepositoryError):
    """Persisted student data cannot safely map to rules input."""


class StudentProfileTransportError(StudentRepositoryError):
    """A safe description of a failed Supabase read."""

    def __init__(self, operation: str, resource: str, *, status_code: int | None = None) -> None:
        detail = f"Student {operation} failed for {resource}"
        if status_code is not None:
            detail += f" (HTTP {status_code})"
        super().__init__(detail)
