from dataclasses import replace

from app.university_onboarding.engine import validate_manifest
from app.university_onboarding.models import (
    CatalogCourse, OnboardingManifest, SourceProvenance, StudyPlanManifest,
)


def manifest() -> OnboardingManifest:
    return OnboardingManifest(
        "1.0", "example-university", "جامعة مثال", "Example University", "Jordan",
        ("IT",), ("CS",),
        (StudyPlanManifest("cs-2026", "CS", "2026", 2026, "6",
                           (CatalogCourse("CS101", "برمجة", "Programming", "3"),
                            CatalogCourse("CS102", "هياكل", "Structures", "3")), "6"),),
        (), (), None,
        (SourceProvenance("https://example.edu/official-plan", "Official plan", "2026-10-22", "official", "sha256:test"),),
    )


def test_dry_run_is_deterministic_and_idempotent():
    first = validate_manifest(manifest())
    second = validate_manifest(manifest())
    assert first == second and first.accepted
    assert first.idempotency_key.startswith("onboard_")


def test_duplicate_course_and_credit_mismatch_fail_closed():
    base = manifest()
    duplicate = replace(base.study_plans[0], total_credit_hours="7", requirement_credit_total="6",
                        courses=base.study_plans[0].courses + (base.study_plans[0].courses[0],))
    report = validate_manifest(replace(base, study_plans=(duplicate,)))
    assert not report.accepted
    assert any(item.startswith("DUPLICATE_COURSE_CODE") for item in report.errors)
    assert any(item.startswith("REQUIREMENT_TOTAL_MISMATCH") for item in report.errors)
    assert report.planned_writes == ()


def test_unresolved_authoritative_source_never_becomes_partial_onboarding():
    report = validate_manifest(replace(manifest(), study_plans=(), unresolved_items=("plan courses",)))
    assert not report.accepted
    assert report.errors == ("NO_STUDY_PLAN_READY", "UNRESOLVED_SOURCE_ITEMS")
