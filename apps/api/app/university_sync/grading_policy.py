"""Closed Fake University grading-policy contract and durable provenance helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from app.university_sync.errors import UniversityProtocolError


FAKE_UNIVERSITY_GRADING_POLICY_V1 = "FAKE_UNIVERSITY_GRADING_POLICY_V1"
FAKE_UNIVERSITY_GPA_MIN = Decimal("0")
FAKE_UNIVERSITY_GPA_MAX = Decimal("100")
FAKE_UNIVERSITY_GPA_SCALE = Decimal("100")
FAKE_UNIVERSITY_COURSE_GRADE_MIN = Decimal("0")
FAKE_UNIVERSITY_COURSE_GRADE_MAX = Decimal("100")


def strict_decimal(value: Any, field: str) -> Decimal:
    """Return one finite decimal without accepting booleans or malformed values."""
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise UniversityProtocolError(f"Malformed university {field}")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as error:
        raise UniversityProtocolError(f"Malformed university {field}") from error
    if not result.is_finite():
        raise UniversityProtocolError(f"Non-finite university {field}")
    return result


def grading_policy_source_reference(university_id: str, version: str) -> str:
    """Format the only accepted durable policy provenance representation."""
    canonical_university = str(UUID(university_id))
    if version != FAKE_UNIVERSITY_GRADING_POLICY_V1:
        raise ValueError("Unsupported university grading-policy version")
    return f"university:{canonical_university}:grading-policy:{version}"


@dataclass(frozen=True)
class ParsedGradingPolicyReference:
    university_id: str
    version: str


def parse_grading_policy_source_reference(value: str | None) -> ParsedGradingPolicyReference | None:
    """Parse a policy reference strictly; malformed or forged values fail closed."""
    if value is None:
        return None
    parts = value.split(":")
    if len(parts) != 4 or parts[0] != "university" or parts[2] != "grading-policy":
        return None
    try:
        university_id = str(UUID(parts[1]))
    except (ValueError, AttributeError, TypeError):
        return None
    version = parts[3]
    if version != FAKE_UNIVERSITY_GRADING_POLICY_V1:
        return None
    return ParsedGradingPolicyReference(university_id, version)
