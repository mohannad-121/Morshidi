"""Dry-run-first, idempotent university onboarding contracts."""

from app.university_onboarding.engine import validate_manifest
from app.university_onboarding.models import OnboardingManifest, OnboardingReport

__all__ = ("OnboardingManifest", "OnboardingReport", "validate_manifest")
