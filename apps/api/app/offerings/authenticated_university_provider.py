"""Owner-scoped offering snapshots from the authenticated university integration."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timedelta, timezone
from typing import Any, Callable

from app.offerings.models import (
    MeetingBlock,
    Modality,
    OfferingPeriod,
    OfferingSection,
    OfferingSnapshot,
    SourceType,
)
from app.offerings.provider import OfferingProviderUnavailable
from app.registration.service import RegistrationService, RegistrationUnavailableError
from app.university_sync.errors import UniversitySyncError


_DAY_NUMBERS = {
    "monday": 1,
    "mon": 1,
    "الاثنين": 1,
    "الإثنين": 1,
    "tuesday": 2,
    "tue": 2,
    "الثلاثاء": 2,
    "wednesday": 3,
    "wed": 3,
    "الأربعاء": 3,
    "الاربعاء": 3,
    "thursday": 4,
    "thu": 4,
    "الخميس": 4,
    "friday": 5,
    "fri": 5,
    "الجمعة": 5,
    "saturday": 6,
    "sat": 6,
    "السبت": 6,
    "sunday": 7,
    "sun": 7,
    "الأحد": 7,
    "الاحد": 7,
}
_OPEN_STATUSES = {"open", "available", "متاحة", "مفتوحة"}
_CLOSED_STATUSES = {"full", "closed", "ممتلئة", "مغلقة"}


class AuthenticatedUniversityOfferingProvider:
    """Build fail-closed snapshots using a student's short-lived upstream token."""

    def __init__(
        self,
        registration: RegistrationService,
        university_id: str,
        *,
        clock: Callable[[], datetime] | None = None,
        freshness: timedelta = timedelta(minutes=5),
    ) -> None:
        if not university_id.strip() or freshness <= timedelta(0):
            raise ValueError("university identity and positive freshness are required")
        self._registration = registration
        self._university_id = university_id
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._freshness = freshness

    async def list_periods(self, university_id: str) -> tuple[OfferingPeriod, ...]:
        """Unscoped access is intentionally unavailable for this student data source."""
        return ()

    async def load_snapshot(self, university_id: str, period_key: str) -> None:
        """Unscoped access is intentionally unavailable for this student data source."""
        return None

    async def list_periods_for_owner(
        self, owner_user_id: str, university_id: str,
    ) -> tuple[OfferingPeriod, ...]:
        if university_id != self._university_id:
            return ()
        try:
            context, manifest = await self._registration.offering_context(owner_user_id)
            period, _, _ = self._period_and_source(context, manifest)
            return (period,)
        except (RegistrationUnavailableError, UniversitySyncError, TypeError, ValueError) as error:
            raise OfferingProviderUnavailable("Authenticated offering source unavailable") from error

    async def load_snapshot_for_owner(
        self, owner_user_id: str, university_id: str, period_key: str,
    ) -> OfferingSnapshot | None:
        if university_id != self._university_id:
            return None
        try:
            context, rows, manifest = await self._registration.offering_source(owner_user_id)
            period, source_type, source_version = self._period_and_source(context, manifest)
            if period.period_key != period_key:
                return None
            sections = tuple(self._section(row, period.provenance) for row in rows)
            if len({section.section_id for section in sections}) != len(sections):
                raise ValueError("duplicate section identity")
            received_at = self._clock()
            if received_at.tzinfo is None:
                raise ValueError("provider clock must be timezone-aware")
            fingerprint = hashlib.sha256(json.dumps(
                [(item.section_id, item.course_code, item.status, item.capacity,
                  item.enrolled, item.available) for item in sections],
                ensure_ascii=False, separators=(",", ":"),
            ).encode("utf-8")).hexdigest()[:20]
            return OfferingSnapshot(
                university_id=university_id,
                period_key=period_key,
                snapshot_id=f"authenticated-{fingerprint}",
                source_version=source_version,
                source_type=source_type,
                source_at=received_at,
                fresh_until=received_at + self._freshness,
                complete=True,
                sections=sections,
                provenance=period.provenance,
            )
        except (RegistrationUnavailableError, UniversitySyncError, TypeError, ValueError) as error:
            raise OfferingProviderUnavailable("Authenticated offering source unavailable") from error

    def _period_and_source(
        self, context_envelope: dict[str, Any], manifest: dict[str, Any],
    ) -> tuple[OfferingPeriod, SourceType, str]:
        if context_envelope.get("success") is not True:
            raise ValueError("registration context was not successful")
        context = context_envelope.get("context")
        if not isinstance(context, dict):
            raise ValueError("registration context is missing")
        term = context.get("term")
        if not isinstance(term, dict):
            raise ValueError("registration term is missing")
        period_key = self._required_text(term.get("code"), "term code")
        label = self._required_text(term.get("label"), "term label")
        if type(context.get("registrationOpen")) is not bool:
            raise ValueError("registration state is missing")

        synthetic = manifest.get("synthetic")
        if type(synthetic) is not bool:
            raise ValueError("source classification is missing")
        if manifest.get("runtime_initialized") is not True:
            raise ValueError("university offering source is not initialized")
        source = self._required_text(manifest.get("source"), "source identity")
        institution = self._required_text(manifest.get("institution_id"), "institution identity")
        active_term = manifest.get("active_term")
        if not isinstance(active_term, dict) or active_term.get("term_id") != period_key:
            raise ValueError("source term does not match registration context")
        source_type = SourceType.SYNTHETIC if synthetic else SourceType.INSTITUTIONAL
        classification = "SYNTHETIC" if synthetic else "INSTITUTIONAL"
        provenance = f"AUTHENTICATED_UNIVERSITY / {classification} / {source} / {institution}"
        source_version = self._required_text(
            manifest.get("fixture_version") or manifest.get("schema_version"), "source version",
        )
        return OfferingPeriod(
            period_key=period_key,
            name_ar=label,
            name_en=label,
            starts_on=None,
            ends_on=None,
            source_type=source_type,
            provenance=provenance,
            registration_open=context["registrationOpen"],
        ), source_type, source_version

    def _section(self, raw: Any, provenance: str) -> OfferingSection:
        if not isinstance(raw, dict):
            raise ValueError("offering row must be an object")
        section_id = self._required_text(raw.get("id") or raw.get("section_id"), "section id")
        course_code = self._required_text(
            raw.get("courseCode") or raw.get("course_code"), "course code",
        )
        capacity = self._nonnegative_int(raw.get("capacity"), "capacity")
        enrolled = self._nonnegative_int(raw.get("enrolled"), "enrolled")
        expected_available = max(0, capacity - enrolled)
        available_raw = raw.get("availableSeats", raw.get("available_seats"))
        available = self._nonnegative_int(available_raw, "available seats")
        if available != expected_available:
            raise ValueError("offering capacity facts are inconsistent")
        status_text = str(raw.get("status") or "").strip().casefold()
        derived_status = "OPEN" if available > 0 else "FULL"
        if status_text not in _OPEN_STATUSES | _CLOSED_STATUSES:
            raise ValueError("offering status is unrecognized")
        if status_text in _OPEN_STATUSES and derived_status != "OPEN":
            raise ValueError("offering status conflicts with capacity")
        if status_text in _CLOSED_STATUSES and derived_status == "OPEN":
            raise ValueError("offering status conflicts with capacity")
        meetings = self._meetings(raw)
        location = str(raw.get("room") or "").strip() or None
        return OfferingSection(
            section_id=section_id,
            course_code=course_code,
            status=derived_status,
            modality=Modality.UNKNOWN,
            campus=None,
            location=location,
            meetings=meetings,
            capacity=capacity,
            enrolled=enrolled,
            available=available,
            waitlist=None,
            provenance=provenance,
            student_visible=True,
        )

    def _meetings(self, raw: dict[str, Any]) -> tuple[MeetingBlock, ...]:
        days = raw.get("daysArray", raw.get("days_array", []))
        if not isinstance(days, list):
            raise ValueError("offering days must be a list")
        if not days:
            return ()
        start_raw = self._required_text(raw.get("startTime") or raw.get("start_time"), "start time")
        end_raw = self._required_text(raw.get("endTime") or raw.get("end_time"), "end time")
        starts_at, ends_at = time.fromisoformat(start_raw), time.fromisoformat(end_raw)
        meetings = []
        for value in days:
            day = _DAY_NUMBERS.get(str(value).strip().casefold())
            if day is None:
                raise ValueError("unrecognized offering day")
            meetings.append(MeetingBlock(day, starts_at, ends_at, "Asia/Amman"))
        return tuple(meetings)

    @staticmethod
    def _required_text(value: Any, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} is required")
        return value.strip()

    @staticmethod
    def _nonnegative_int(value: Any, field: str) -> int:
        if type(value) is not int or value < 0:
            raise ValueError(f"{field} must be a nonnegative integer")
        return value
