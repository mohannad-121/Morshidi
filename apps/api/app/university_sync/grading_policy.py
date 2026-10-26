"""Closed Fake University and extensible universal institutional grading-policy contracts.

Supports:
1. 100-point percentage scale (Jordanian style: 0-100, pass 50 or 60, scale 100).
2. 4.0 GPA scale (US / Gulf style: 0.00-4.00, pass 2.0).
3. 4.33 GPA scale (0.00-4.33).
4. 5.0 GPA scale (Saudi / regional style: 0.00-5.00, pass 2.75).
5. Letter grade policies (A+, A, A-, B+, etc.).

Principle: THE UNIVERSITY SIS REMAINS AUTHORITATIVE. AI EXPLAINS — DETERMINISTIC RULES DECIDE.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any
from uuid import UUID

from app.university_sync.errors import UniversityProtocolError

# Predefined standard policy version identifiers
FAKE_UNIVERSITY_GRADING_POLICY_V1 = "FAKE_UNIVERSITY_GRADING_POLICY_V1"
UNIVERSAL_PERCENTAGE_100_V1 = "UNIVERSAL_PERCENTAGE_100_V1"
UNIVERSAL_GPA_4_V1 = "UNIVERSAL_GPA_4_V1"
UNIVERSAL_GPA_433_V1 = "UNIVERSAL_GPA_433_V1"
UNIVERSAL_GPA_5_V1 = "UNIVERSAL_GPA_5_V1"
UNIVERSAL_LETTER_V1 = "UNIVERSAL_LETTER_V1"

SUPPORTED_POLICY_VERSIONS: frozenset[str] = frozenset({
    FAKE_UNIVERSITY_GRADING_POLICY_V1,
    UNIVERSAL_PERCENTAGE_100_V1,
    UNIVERSAL_GPA_4_V1,
    UNIVERSAL_GPA_433_V1,
    UNIVERSAL_GPA_5_V1,
    UNIVERSAL_LETTER_V1,
})

# Backward compatibility constants for Fake University
FAKE_UNIVERSITY_GPA_MIN = Decimal("0")
FAKE_UNIVERSITY_GPA_MAX = Decimal("100")
FAKE_UNIVERSITY_GPA_SCALE = Decimal("100")
FAKE_UNIVERSITY_COURSE_GRADE_MIN = Decimal("0")
FAKE_UNIVERSITY_COURSE_GRADE_MAX = Decimal("100")


class GradingScaleType(str, Enum):
    PERCENTAGE_100 = "PERCENTAGE_100"
    GPA_4_0 = "GPA_4_0"
    GPA_4_33 = "GPA_4_33"
    GPA_5_0 = "GPA_5_0"
    LETTER_GRADE = "LETTER_GRADE"


@dataclass(frozen=True)
class LetterGradeMapping:
    """One discrete letter-grade bracket with corresponding grade points."""

    letter: str
    min_grade: Decimal
    max_grade: Decimal
    grade_points: Decimal


@dataclass(frozen=True)
class InstitutionalGradingPolicy:
    """Universal configuration for an institution's grading system."""

    university_id: str
    policy_version: str
    scale_type: GradingScaleType
    gpa_scale: Decimal
    gpa_min: Decimal
    gpa_max: Decimal
    course_grade_min: Decimal
    course_grade_max: Decimal
    passing_grade: Decimal
    major_passing_grade: Decimal
    warning_threshold: Decimal
    honors_threshold: Decimal
    letter_grade_mappings: tuple[LetterGradeMapping, ...] = ()

    def is_grade_passing(self, grade: Decimal, is_major: bool = False) -> bool:
        """Deterministic pass/fail rule."""
        threshold = self.major_passing_grade if is_major else self.passing_grade
        return grade >= threshold

    def is_gpa_on_warning(self, gpa: Decimal) -> bool:
        """Deterministic academic warning rule."""
        return gpa < self.warning_threshold

    def is_gpa_honors(self, gpa: Decimal) -> bool:
        """Deterministic honors qualification rule."""
        return gpa >= self.honors_threshold

    def normalize_to_percentage(self, value: Decimal) -> int:
        """Map raw grade or GPA to 0..100 percentage scale for unified analytics."""
        if not value.is_finite() or self.course_grade_max <= self.course_grade_min:
            return 0
        clamped = min(max(value, self.course_grade_min), self.course_grade_max)
        span = self.course_grade_max - self.course_grade_min
        return round((clamped - self.course_grade_min) * 100 / span)


# Factory for standard institutional grading policies
def create_standard_policy(
    policy_version: str, university_id: str = "00000000-0000-0000-0000-000000000000"
) -> InstitutionalGradingPolicy:
    if policy_version in (FAKE_UNIVERSITY_GRADING_POLICY_V1, UNIVERSAL_PERCENTAGE_100_V1):
        return InstitutionalGradingPolicy(
            university_id=university_id,
            policy_version=policy_version,
            scale_type=GradingScaleType.PERCENTAGE_100,
            gpa_scale=Decimal("100"),
            gpa_min=Decimal("0"),
            gpa_max=Decimal("100"),
            course_grade_min=Decimal("0"),
            course_grade_max=Decimal("100"),
            passing_grade=Decimal("50"),
            major_passing_grade=Decimal("60"),
            warning_threshold=Decimal("60"),
            honors_threshold=Decimal("84"),
            letter_grade_mappings=(
                LetterGradeMapping("A+", Decimal("90"), Decimal("100"), Decimal("4.0")),
                LetterGradeMapping("A", Decimal("85"), Decimal("89"), Decimal("3.75")),
                LetterGradeMapping("B+", Decimal("80"), Decimal("84"), Decimal("3.5")),
                LetterGradeMapping("B", Decimal("75"), Decimal("79"), Decimal("3.0")),
                LetterGradeMapping("C+", Decimal("70"), Decimal("74"), Decimal("2.5")),
                LetterGradeMapping("C", Decimal("60"), Decimal("69"), Decimal("2.0")),
                LetterGradeMapping("D", Decimal("50"), Decimal("59"), Decimal("1.5")),
                LetterGradeMapping("F", Decimal("0"), Decimal("49"), Decimal("0.0")),
            ),
        )
    if policy_version == UNIVERSAL_GPA_4_V1:
        return InstitutionalGradingPolicy(
            university_id=university_id,
            policy_version=policy_version,
            scale_type=GradingScaleType.GPA_4_0,
            gpa_scale=Decimal("4.0"),
            gpa_min=Decimal("0.0"),
            gpa_max=Decimal("4.0"),
            course_grade_min=Decimal("0.0"),
            course_grade_max=Decimal("4.0"),
            passing_grade=Decimal("2.0"),
            major_passing_grade=Decimal("2.0"),
            warning_threshold=Decimal("2.0"),
            honors_threshold=Decimal("3.5"),
            letter_grade_mappings=(
                LetterGradeMapping("A", Decimal("3.75"), Decimal("4.0"), Decimal("4.0")),
                LetterGradeMapping("B", Decimal("2.75"), Decimal("3.74"), Decimal("3.0")),
                LetterGradeMapping("C", Decimal("2.0"), Decimal("2.74"), Decimal("2.0")),
                LetterGradeMapping("D", Decimal("1.0"), Decimal("1.99"), Decimal("1.0")),
                LetterGradeMapping("F", Decimal("0.0"), Decimal("0.99"), Decimal("0.0")),
            ),
        )
    if policy_version == UNIVERSAL_GPA_433_V1:
        return InstitutionalGradingPolicy(
            university_id=university_id,
            policy_version=policy_version,
            scale_type=GradingScaleType.GPA_4_33,
            gpa_scale=Decimal("4.33"),
            gpa_min=Decimal("0.0"),
            gpa_max=Decimal("4.33"),
            course_grade_min=Decimal("0.0"),
            course_grade_max=Decimal("4.33"),
            passing_grade=Decimal("2.0"),
            major_passing_grade=Decimal("2.0"),
            warning_threshold=Decimal("2.0"),
            honors_threshold=Decimal("3.7"),
        )
    if policy_version == UNIVERSAL_GPA_5_V1:
        return InstitutionalGradingPolicy(
            university_id=university_id,
            policy_version=policy_version,
            scale_type=GradingScaleType.GPA_5_0,
            gpa_scale=Decimal("5.0"),
            gpa_min=Decimal("0.0"),
            gpa_max=Decimal("5.0"),
            course_grade_min=Decimal("0.0"),
            course_grade_max=Decimal("5.0"),
            passing_grade=Decimal("2.75"),
            major_passing_grade=Decimal("3.0"),
            warning_threshold=Decimal("2.75"),
            honors_threshold=Decimal("4.5"),
        )
    raise ValueError(f"Unknown standard grading policy version: {policy_version}")


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


_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,64}$")


def is_valid_policy_version(version: str) -> bool:
    """Check if version format is valid and matches supported policy versions."""
    return bool(version in SUPPORTED_POLICY_VERSIONS or _VERSION_PATTERN.match(version))


def grading_policy_source_reference(university_id: str, version: str) -> str:
    """Format the durable policy provenance representation for any supported institutional version."""
    canonical_university = str(UUID(university_id))
    if not is_valid_policy_version(version):
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
    if not is_valid_policy_version(version):
        return None
    return ParsedGradingPolicyReference(university_id, version)
