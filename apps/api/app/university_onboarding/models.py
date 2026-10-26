"""Portable manifest models; they contain no credentials or production actions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SourceProvenance:
    source_url: str
    title: str
    retrieved_on: str
    source_status: str
    content_hash: str | None = None


@dataclass(frozen=True)
class CatalogCourse:
    course_code: str
    name_ar: str | None
    name_en: str | None
    credit_hours: str


@dataclass(frozen=True)
class StudyPlanManifest:
    external_key: str
    program_external_key: str
    plan_number: str
    effective_year: int | None
    total_credit_hours: str
    courses: tuple[CatalogCourse, ...] = ()
    requirement_credit_total: str | None = None


@dataclass(frozen=True)
class OnboardingManifest:
    manifest_version: str
    university_external_key: str
    university_name_ar: str
    university_name_en: str
    country: str
    faculties: tuple[str, ...]
    programs: tuple[str, ...]
    study_plans: tuple[StudyPlanManifest, ...]
    policy_package_refs: tuple[str, ...]
    learning_material_refs: tuple[str, ...]
    offering_provider_ref: str | None
    sources: tuple[SourceProvenance, ...]
    unresolved_items: tuple[str, ...] = ()


@dataclass(frozen=True)
class OnboardingReport:
    idempotency_key: str
    accepted: bool
    counts: dict[str, int]
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    planned_writes: tuple[str, ...] = field(default_factory=tuple)
