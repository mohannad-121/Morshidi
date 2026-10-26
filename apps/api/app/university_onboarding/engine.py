"""Deterministic onboarding validation. It never writes to a database."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json

from app.university_onboarding.models import OnboardingManifest, OnboardingReport


def _fingerprint(manifest: OnboardingManifest) -> str:
    payload = json.dumps(asdict(manifest), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "onboard_" + sha256(payload.encode("utf-8")).hexdigest()


def validate_manifest(manifest: OnboardingManifest) -> OnboardingReport:
    """Return the same report for the same manifest; unresolved authority fails closed."""
    errors: list[str] = []
    warnings: list[str] = []
    if manifest.manifest_version != "1.0":
        errors.append("UNSUPPORTED_MANIFEST_VERSION")
    if not manifest.university_external_key or not manifest.sources:
        errors.append("UNIVERSITY_IDENTITY_OR_PROVENANCE_MISSING")
    if any(source.source_status != "official" for source in manifest.sources):
        errors.append("NON_OFFICIAL_SOURCE")
    if manifest.unresolved_items:
        errors.append("UNRESOLVED_SOURCE_ITEMS")
    if not manifest.study_plans:
        errors.append("NO_STUDY_PLAN_READY")

    seen_plan_keys: set[str] = set()
    for plan in manifest.study_plans:
        if plan.external_key in seen_plan_keys:
            errors.append(f"DUPLICATE_PLAN_KEY:{plan.external_key}")
        seen_plan_keys.add(plan.external_key)
        codes = [course.course_code for course in plan.courses]
        if len(codes) != len(set(codes)):
            errors.append(f"DUPLICATE_COURSE_CODE:{plan.external_key}")
        try:
            total = Decimal(plan.total_credit_hours)
            listed = sum((Decimal(course.credit_hours) for course in plan.courses), Decimal("0"))
            requirement_total = Decimal(plan.requirement_credit_total) if plan.requirement_credit_total else None
        except InvalidOperation:
            errors.append(f"INVALID_CREDIT_VALUE:{plan.external_key}")
            continue
        if total < 0 or any(Decimal(course.credit_hours) < 0 for course in plan.courses):
            errors.append(f"NEGATIVE_CREDIT_VALUE:{plan.external_key}")
        if requirement_total is not None and requirement_total != total:
            errors.append(f"REQUIREMENT_TOTAL_MISMATCH:{plan.external_key}")
        if plan.courses and listed < total:
            warnings.append(f"COURSE_LIST_DOES_NOT_FULLY_ACCOUNT_FOR_PLAN:{plan.external_key}")

    accepted = not errors
    counts = {
        "faculties": len(manifest.faculties),
        "programs": len(manifest.programs),
        "study_plans": len(manifest.study_plans),
        "courses": sum(len(plan.courses) for plan in manifest.study_plans),
        "policy_packages": len(manifest.policy_package_refs),
        "learning_material_sets": len(manifest.learning_material_refs),
    }
    return OnboardingReport(
        idempotency_key=_fingerprint(manifest),
        accepted=accepted,
        counts=counts,
        errors=tuple(sorted(set(errors))),
        warnings=tuple(sorted(set(warnings))),
        planned_writes=(
            "universities", "faculties", "majors", "study_plans", "requirement_groups",
            "courses", "study_plan_courses", "academic_sources",
        ) if accepted else (),
    )
