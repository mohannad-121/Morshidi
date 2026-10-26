"""Universal Course Identity and Terminology Resolution Engine.

Distinguishes between:
1. Search & terminology aliases (helps students find courses across dialects, historical codes, and naming variants).
2. Authoritative academic course equivalencies (strict institutional rules for prerequisites, credit transfers, and graduation audits).

ARCHITECTURAL INVARIANT:
AI EXPLAINS — DETERMINISTIC RULES DECIDE.
- Terminology matching aids student discovery and offerings autocomplete.
- Only verified institutional equivalency records in public.course_equivalencies decide academic validity.
- LLMs or fuzzy similarity must NEVER declare course equivalencies without verified institutional configuration.
"""

from __future__ import annotations

import re
import unicodedata
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CourseAliasType(str, Enum):
    INSTITUTIONAL_NAME = "INSTITUTIONAL_NAME"
    SEARCH_SYNONYM = "SEARCH_SYNONYM"
    HISTORICAL_CODE = "HISTORICAL_CODE"
    REGIONAL_VARIANT = "REGIONAL_VARIANT"


class InstitutionalCourseAlias(BaseModel):
    """A terminology or search alias mapping to a canonical course."""

    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    university_id: str
    canonical_course_code: str
    alias_code: str | None = None
    alias_name_ar: str
    alias_name_en: str | None = None
    alias_type: CourseAliasType = CourseAliasType.INSTITUTIONAL_NAME
    is_verified: bool = True
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UniversalCourseIdentity(BaseModel):
    """Canonical university-agnostic course representation."""

    model_config = ConfigDict(extra="ignore")

    canonical_id: str
    canonical_code: str
    name_ar: str
    name_en: str | None = None
    credit_hours: Decimal = Field(default=Decimal("3.0"))
    department_code: str | None = None
    faculty_code: str | None = None
    status: str = "ACTIVE"
    aliases: list[InstitutionalCourseAlias] = Field(default_factory=list)
    extension_attributes: dict[str, Any] = Field(default_factory=dict)


class CourseEquivalencyRecord(BaseModel):
    """Authoritative academic equivalency record from public.course_equivalencies."""

    model_config = ConfigDict(extra="ignore")

    source_course_code: str
    target_course_code: str
    relationship_type: Literal["equivalent", "replacement", "legacy_code"] = "equivalent"
    is_bidirectional: bool = False
    verification_status: Literal["verified", "pending", "unresolved", "rejected"] = "verified"
    notes: str | None = None


def normalize_arabic_terminology(text: str) -> str:
    """Normalize Arabic text for terminology matching without mutating canonical identities."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text).strip().lower()
    # Strip tashkeel diacritics
    normalized = re.sub(r"[\u064b-\u065f\u0670]", "", normalized)
    # Strip tatweel/kashida
    normalized = re.sub(r"\u0640", "", normalized)
    # Unify Alef variants
    normalized = re.sub(r"[أإآٱ]", "ا", normalized)
    # Unify Alif Maqsura
    normalized = re.sub(r"ى", "ي", normalized)
    # Map Ta Marbuta to Ha for relaxed search
    normalized = re.sub(r"ة", "ه", normalized)
    # Map Eastern Arabic numerals to Western digits
    normalized = normalized.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    # Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


class CourseAliasResolver:
    """Resolves search and terminology aliases within an institutional tenant boundary."""

    def __init__(
        self,
        university_id: str,
        courses: list[UniversalCourseIdentity] | None = None,
        aliases: list[InstitutionalCourseAlias] | None = None,
        equivalencies: list[CourseEquivalencyRecord] | None = None,
    ) -> None:
        self.university_id = university_id
        self._courses_by_code: dict[str, UniversalCourseIdentity] = {}
        self._aliases: list[InstitutionalCourseAlias] = []
        self._equivalencies: list[CourseEquivalencyRecord] = equivalencies or []

        if courses:
            for c in courses:
                self._courses_by_code[c.canonical_code.strip().upper()] = c

        if aliases:
            for a in aliases:
                self.add_alias(a)

    def add_alias(self, alias: InstitutionalCourseAlias) -> None:
        if alias.university_id != self.university_id:
            return  # Strict tenant isolation
        self._aliases.append(alias)
        code_key = alias.canonical_course_code.strip().upper()
        if code_key in self._courses_by_code:
            course = self._courses_by_code[code_key]
            if alias not in course.aliases:
                course.aliases.append(alias)

    def get_aliases_for_course(self, canonical_course_code: str) -> list[InstitutionalCourseAlias]:
        code = canonical_course_code.strip().upper()
        return [a for a in self._aliases if a.canonical_course_code.strip().upper() == code]

    def search_courses(self, query: str) -> list[tuple[UniversalCourseIdentity, float, str]]:
        """Search canonical courses and aliases, returning (course, score, matched_label)."""
        norm_query = normalize_arabic_terminology(query)
        if not norm_query:
            return []

        results: list[tuple[UniversalCourseIdentity, float, str]] = []
        seen_codes: set[str] = set()

        # 1. Match canonical courses
        for code, course in self._courses_by_code.items():
            norm_name = normalize_arabic_terminology(course.name_ar)
            norm_code = course.canonical_code.strip().lower()
            norm_en = (course.name_en or "").strip().lower()

            if norm_query == norm_name or norm_query == norm_code:
                results.append((course, 1000.0, course.name_ar))
                seen_codes.add(code)
            elif norm_name.startswith(norm_query) or norm_code.startswith(norm_query):
                results.append((course, 800.0, course.name_ar))
                seen_codes.add(code)
            elif norm_query in norm_name or norm_query in norm_en:
                results.append((course, 500.0, course.name_ar))
                seen_codes.add(code)

        # 2. Match aliases (synonyms, regional variants, historical codes)
        for alias in self._aliases:
            canon_code = alias.canonical_course_code.strip().upper()
            course = self._courses_by_code.get(canon_code)
            if not course or canon_code in seen_codes:
                continue

            norm_alias_ar = normalize_arabic_terminology(alias.alias_name_ar)
            alias_code = (alias.alias_code or "").strip().lower()

            if norm_query == norm_alias_ar or norm_query == alias_code:
                results.append((course, 900.0, f"{course.name_ar} ({alias.alias_name_ar})"))
                seen_codes.add(canon_code)
            elif norm_alias_ar.startswith(norm_query):
                results.append((course, 700.0, f"{course.name_ar} ({alias.alias_name_ar})"))
                seen_codes.add(canon_code)
            elif norm_query in norm_alias_ar:
                results.append((course, 400.0, f"{course.name_ar} ({alias.alias_name_ar})"))
                seen_codes.add(canon_code)

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def is_academically_equivalent(self, course_a: str, course_b: str) -> bool:
        """Deterministic institutional equivalency evaluation.
        
        CRITICAL: Never relies on terminology aliases, fuzzy similarity, or LLM interpretation.
        Only verified records in public.course_equivalencies decide academic equivalency.
        """
        code_a = course_a.strip().upper()
        code_b = course_b.strip().upper()
        if code_a == code_b:
            return True

        for eq in self._equivalencies:
            if eq.verification_status != "verified":
                continue
            src = eq.source_course_code.strip().upper()
            tgt = eq.target_course_code.strip().upper()
            if src == code_a and tgt == code_b:
                return True
            if eq.is_bidirectional and src == code_b and tgt == code_a:
                return True
        return False
