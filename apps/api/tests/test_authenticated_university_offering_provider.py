from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from app.offerings.authenticated_university_provider import AuthenticatedUniversityOfferingProvider
from app.offerings.models import SourceType
from app.offerings.provider import OfferingProviderUnavailable


UNIVERSITY = "10000000-0000-0000-0000-000000000010"
OTHER_UNIVERSITY = "10000000-0000-0000-0000-000000000099"
NOW = datetime(2026, 10, 25, 9, 0, tzinfo=timezone.utc)


def _context(*, open_: bool = True):
    return {
        "success": True,
        "context": {
            "term": {"code": "2026-1", "label": "الفصل الأول 2026/2027"},
            "registrationOpen": open_,
        },
    }


def _manifest(*, synthetic: bool = True):
    return {
        "schema_version": "1.0.0",
        "fixture_version": "2026.10.12.v2",
        "institution_id": "morshidi-sandbox" if synthetic else "real-university",
        "synthetic": synthetic,
        "runtime_initialized": True,
        "source": "MORSHIDI_SANDBOX_UNIVERSITY" if synthetic else "UNIVERSITY_SIS",
        "active_term": {"term_id": "2026-1", "name": "Fall"},
    }


def _section(**changes):
    row = {
        "id": "SEC-1501101-1",
        "courseCode": "1501101",
        "status": "متاحة",
        "daysArray": ["الأحد", "Tuesday"],
        "startTime": "09:00",
        "endTime": "10:30",
        "room": "A-101",
        "capacity": 30,
        "enrolled": 20,
        "availableSeats": 10,
    }
    row.update(changes)
    return row


class RegistrationSource:
    def __init__(self, *, rows=None, manifest=None):
        self.rows = [_section()] if rows is None else rows
        self.manifest = _manifest() if manifest is None else manifest
        self.calls = []

    async def offering_context(self, owner):
        self.calls.append(("context", owner))
        return _context(), self.manifest

    async def offering_source(self, owner):
        self.calls.append(("source", owner))
        return _context(), self.rows, self.manifest


def _provider(source):
    return AuthenticatedUniversityOfferingProvider(source, UNIVERSITY, clock=lambda: NOW)


def test_authenticated_synthetic_source_is_visible_and_owner_scoped():
    source = RegistrationSource()
    provider = _provider(source)

    periods = asyncio.run(provider.list_periods_for_owner("owner-a", UNIVERSITY))
    snapshot = asyncio.run(provider.load_snapshot_for_owner("owner-a", UNIVERSITY, "2026-1"))

    assert periods[0].registration_open is True
    assert periods[0].source_type is SourceType.SYNTHETIC
    assert "SYNTHETIC" in periods[0].provenance
    assert snapshot is not None
    assert snapshot.source_type is SourceType.SYNTHETIC
    assert snapshot.source_at == NOW
    assert snapshot.complete is True
    assert snapshot.sections[0].course_code == "1501101"
    assert snapshot.sections[0].student_visible is True
    assert [meeting.day for meeting in snapshot.sections[0].meetings] == [7, 2]
    assert source.calls == [("context", "owner-a"), ("source", "owner-a")]


def test_institutional_manifest_is_not_mislabeled_synthetic():
    provider = _provider(RegistrationSource(manifest=_manifest(synthetic=False)))
    snapshot = asyncio.run(provider.load_snapshot_for_owner("owner", UNIVERSITY, "2026-1"))
    assert snapshot is not None
    assert snapshot.source_type is SourceType.INSTITUTIONAL
    assert "INSTITUTIONAL" in snapshot.provenance


def test_complete_empty_source_is_distinct_from_unavailable_source():
    provider = _provider(RegistrationSource(rows=[]))
    snapshot = asyncio.run(provider.load_snapshot_for_owner("owner", UNIVERSITY, "2026-1"))
    assert snapshot is not None
    assert snapshot.complete is True
    assert snapshot.sections == ()


def test_cross_tenant_and_wrong_period_fail_closed_without_fallback():
    source = RegistrationSource()
    provider = _provider(source)
    assert asyncio.run(provider.list_periods_for_owner("owner", OTHER_UNIVERSITY)) == ()
    assert asyncio.run(provider.load_snapshot_for_owner("owner", OTHER_UNIVERSITY, "2026-1")) is None
    assert source.calls == []
    assert asyncio.run(provider.load_snapshot_for_owner("owner", UNIVERSITY, "2027-1")) is None


@pytest.mark.parametrize(
    "source",
    [
        RegistrationSource(manifest={**_manifest(), "synthetic": None}),
        RegistrationSource(manifest={**_manifest(), "runtime_initialized": False}),
        RegistrationSource(manifest={**_manifest(), "active_term": {"term_id": "2027-1"}}),
        RegistrationSource(rows=[_section(availableSeats=9)]),
        RegistrationSource(rows=[_section(daysArray=["NotADay"])]),
    ],
)
def test_missing_provenance_or_inconsistent_facts_are_unavailable(source):
    with pytest.raises(OfferingProviderUnavailable, match="source unavailable"):
        asyncio.run(_provider(source).load_snapshot_for_owner("owner", UNIVERSITY, "2026-1"))


def test_unscoped_methods_never_expose_student_specific_source():
    source = RegistrationSource()
    provider = _provider(source)
    assert asyncio.run(provider.list_periods(UNIVERSITY)) == ()
    assert asyncio.run(provider.load_snapshot(UNIVERSITY, "2026-1")) is None
    assert source.calls == []
