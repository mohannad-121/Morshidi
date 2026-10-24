"""One-call, period-scoped provider interface; no live provider is implied."""

from __future__ import annotations

from typing import Protocol

from .models import OfferingPeriod, OfferingSnapshot


class OfferingProviderUnavailable(RuntimeError):
    """Safe adapter signal for timeout, transport failure, or source outage."""


class CourseOfferingProvider(Protocol):
    async def list_periods(self, university_id: str) -> tuple[OfferingPeriod, ...]:
        """Return discoverable periods for this exact tenant only."""

    async def load_snapshot(self, university_id: str, period_key: str) -> OfferingSnapshot | None:
        """Return None on unavailable data, not a claim that no course is offered."""


class UnavailableOfferingProvider:
    async def list_periods(self, university_id: str) -> tuple[OfferingPeriod, ...]:
        return ()

    async def load_snapshot(self, university_id: str, period_key: str) -> None:
        return None
