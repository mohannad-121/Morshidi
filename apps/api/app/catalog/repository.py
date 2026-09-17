"""The narrow read contract used by future eligibility application code."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.rules.models import CanTakeCatalog
from app.progress.models import AcademicProgressCatalog


class AcademicCatalogRepository(Protocol):
    """Loads one resolved plan target as the canonical pure-engine snapshot.

    TODO(Phase 5.4): replace raw database UUID exposure with a stable public
    study-plan selector once the catalog defines one.
    """

    async def load_target_rules(
        self,
        study_plan_id: UUID | str,
        target_course_code: str,
    ) -> CanTakeCatalog:
        """Return the resolved target and dependency identities for CAN TAKE."""

    async def load_progress_catalog(
        self,
        study_plan_id: UUID | str,
    ) -> AcademicProgressCatalog:
        """Return one complete, explicitly ordered plan snapshot for progress."""
