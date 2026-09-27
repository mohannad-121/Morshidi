"""Pydantic schemas for student-facing institutional policy endpoints (WC-038).

AI EXPLAINS — DETERMINISTIC RULES DECIDE.
Strictly typed read-only models for verified university regulations and institutional policies.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class StudentPolicyPassageResponse(BaseModel):
    """A single cited passage within a verified policy version."""

    model_config = ConfigDict(extra="ignore")

    id: str
    locator_text: str
    passage_text: str
    article_number: str | None = None
    section_number: str | None = None
    page_number: int | None = None
    heading: str | None = None
    sequence_order: int = 0
    passage_sha256: str | None = None


class StudentPolicyDocumentSummary(BaseModel):
    """Summary of a verified institutional policy document."""

    model_config = ConfigDict(extra="ignore")

    id: str
    university_id: str
    document_code: str
    title: str
    authority_level: str
    category: str
    language: str = "ar"
    active_version_tag: str
    effective_start_date: Any | None = None
    passage_count: int = 0


class StudentPolicyVersionDetail(BaseModel):
    """Metadata of the active verified policy version."""

    model_config = ConfigDict(extra="ignore")

    id: str
    version_tag: str
    status: str
    effective_start_date: Any | None = None
    effective_end_date: Any | None = None
    content_sha256: str | None = None
    verified_at: Any | None = None
    verified_by: str | None = None
    source_url: str | None = None


class StudentPolicyDocumentDetail(BaseModel):
    """Full detail of a verified institutional policy document with passages."""

    model_config = ConfigDict(extra="ignore")

    id: str
    university_id: str
    document_code: str
    title: str
    authority_level: str
    category: str
    language: str = "ar"
    active_version: StudentPolicyVersionDetail
    passages: list[StudentPolicyPassageResponse] = Field(default_factory=list)


class StudentPolicySearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document_id: str
    document_code: str
    document_title: str
    category: str
    version_id: str
    version_tag: str
    status: str
    effective_start_date: Any | None = None
    effective_end_date: Any | None = None
    content_sha256: str | None = None
    verified_at: Any | None = None
    verified_by: str | None = None
    source_url: str | None = None
    passage_id: str
    sequence_order: int
    passage_text: str
    locator_text: str
    article_number: str | None = None
    section_number: str | None = None
    page_number: int | None = None
    heading: str | None = None
    passage_sha256: str | None = None
