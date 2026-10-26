"""Checked-in authoritative policies until the approved DB repository is wired."""

from datetime import date
from decimal import Decimal

from app.graduation_policy.models import (
    GraduationPolicyRegistry,
    GraduationPolicyRule,
    GraduationPolicyVersion,
    PolicyLifecycleStatus,
    PolicyRuleKind,
    PolicyScope,
    PolicyScopeLevel,
)

ZU_UNIVERSITY_ID = "10000000-0000-0000-0000-000000000001"
AI_PLAN_12_ID = "10000000-0000-0000-0000-000000000005"
AI_PROJECT_CODES = ("1505467", "1505468")

AI_PLAN_12_POLICY = GraduationPolicyVersion(
    policy_id="ZU_AI_P12_GRADUATION_POLICY",
    version="P15_5_PROJECT_CREDITS_V1",
    scope=PolicyScope(
        level=PolicyScopeLevel.STUDY_PLAN,
        university_id=ZU_UNIVERSITY_ID,
        study_plan_id=AI_PLAN_12_ID,
    ),
    status=PolicyLifecycleStatus.APPROVED,
    effective_from=date(2026, 10, 16),
    effective_to=None,
    rules=(
        GraduationPolicyRule(
            rule_id="GRADUATION_PROJECT_MIN_EARNED_CREDITS",
            version="P15_5_PROJECT_CREDITS_V1",
            kind=PolicyRuleKind.MIN_EARNED_CREDITS_FOR_COURSE,
            provenance="OWNER_APPROVED_PLAN12_PROJECT_REQUIREMENT",
            target_course_codes=AI_PROJECT_CODES,
            minimum_credits=Decimal("90"),
            source_reference="Morshidi P15.5 owner-approved Plan 12 project rule",
        ),
    ),
)

DEFAULT_GRADUATION_POLICY_REGISTRY = GraduationPolicyRegistry((AI_PLAN_12_POLICY,))
