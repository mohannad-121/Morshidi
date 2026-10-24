"""Typed policy resolution and database-governance regression tests."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from app.graduation_policy.catalog import AI_PLAN_12_ID, DEFAULT_GRADUATION_POLICY_REGISTRY
from app.graduation_policy.models import (
    GraduationPolicyRegistry,
    GraduationPolicyRule,
    GraduationPolicyVersion,
    PolicyLifecycleStatus,
    PolicyRuleKind,
    PolicyScope,
    PolicyScopeLevel,
)


def _policy(status: PolicyLifecycleStatus, plan_id: str = "plan-a") -> GraduationPolicyVersion:
    return GraduationPolicyVersion(
        policy_id="policy-a",
        version="v1",
        scope=PolicyScope(PolicyScopeLevel.STUDY_PLAN, "university-a", study_plan_id=plan_id),
        status=status,
        effective_from=date(2026, 1, 1),
        effective_to=None,
        rules=(GraduationPolicyRule(
            "RULE", "v1", PolicyRuleKind.MIN_EARNED_CREDITS_FOR_COURSE,
            "approved-source", ("COURSE-1",), Decimal("90"),
        ),),
    )


def test_registry_requires_exact_plan_course_approved_and_effective_scope():
    registry = GraduationPolicyRegistry((
        _policy(PolicyLifecycleStatus.DRAFT),
        _policy(PolicyLifecycleStatus.APPROVED, "plan-b"),
    ))
    assert registry.rules_for_course("plan-a", "COURSE-1", on_date=date(2026, 2, 1)) == ()
    assert len(registry.rules_for_course("plan-b", "COURSE-1", on_date=date(2026, 2, 1))) == 1
    assert registry.rules_for_course("plan-b", "OTHER", on_date=date(2026, 2, 1)) == ()


def test_authoritative_ai_policy_does_not_leak_to_another_plan():
    assert DEFAULT_GRADUATION_POLICY_REGISTRY.rules_for_course(
        AI_PLAN_12_ID, "1505467", on_date=date(2026, 10, 22)
    )
    assert DEFAULT_GRADUATION_POLICY_REGISTRY.rules_for_course(
        "2a78bbbb-0dc0-5c46-8630-7a46e4179830", "1505467", on_date=date(2026, 10, 22)
    ) == ()


def test_policy_migration_has_governance_scope_rls_and_no_client_write_grant():
    migration = Path("supabase/migrations/20261022141020_add_versioned_graduation_policies.sql").read_text()
    assert "'draft', 'validated', 'approved', 'retired'" in migration
    assert "'university', 'degree_level', 'faculty', 'program', 'study_plan'" in migration
    assert migration.count("enable row level security") == 6
    assert "from public, anon, authenticated" in migration
    assert "grant select, insert, update, delete on table public.graduation_policy_versions to authenticated" not in migration
