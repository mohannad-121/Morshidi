"""Read-only student academic-state contract."""

from typing import Protocol
from uuid import UUID

from app.student.models import StudentAcademicState


class StudentAcademicRepository(Protocol):
    async def load_student_academic_state(
        self, owner_user_id: UUID | str
    ) -> StudentAcademicState:
        """Load one owner's profile and every persisted attempt."""
