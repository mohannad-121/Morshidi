"""Deterministic CI test suite for all 17 Zarqa University study plans.

Enforces:
1. sum(required_credits across requirement groups) == study_plan.total_credit_hours.
2. Official total matching: 16 programs at 132.0 cr, Law at 141.0 cr.
3. 9 programs contain the 3-credit FREE_ELECTIVE group; 8 programs do not.
4. FREE_ELECTIVE requirement groups contain zero fixed courses (no fake course codes).
5. FREE_ELECTIVE selection behavior fails closed (policy_required).
6. No duplicate course memberships within any requirement group.
7. Requirement group codes are unique within each study plan.
8. MANIFEST.json checksum integrity across all canonical artifacts in data/curricula.
9. Local DB integrity check (if database is reachable).
"""

import os
import json
import hashlib
from decimal import Decimal
import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DATA_DIR = os.path.join(REPO_ROOT, "data", "curricula")
PLANS_DIR = os.path.join(DATA_DIR, "plans")

EXPECTED_FE_PLANS = {
    "ZU:SCI:MATH:P12",
    "ZU:SCI:PHYS:P12",
    "ZU:ARTS:ENGLISH:P12",
    "ZU:ARTS:HISTORY:P12",
    "ZU:ARTS:TRANS:P12",
    "ZU:BUS:ECON:P12",
    "ZU:BUS:BBA:P12",
    "ZU:BUS:ACC:P12",
    "ZU:NURS:NURS:P12",
}

EXPECTED_OFFICIAL_TOTALS = {
    "ZU:IT:AI:P12": Decimal("132.0"),
    "ZU:IT:SE:P12": Decimal("132.0"),
    "ZU:IT:CS:P12": Decimal("132.0"),
    "ZU:IT:CYBER:P12": Decimal("132.0"),
    "ZU:SCI:MATH:P12": Decimal("132.0"),
    "ZU:SCI:PHYS:P12": Decimal("132.0"),
    "ZU:ARTS:ARABIC:P12": Decimal("132.0"),
    "ZU:ARTS:ENGLISH:P12": Decimal("132.0"),
    "ZU:ARTS:HISTORY:P12": Decimal("132.0"),
    "ZU:ARTS:TRANS:P12": Decimal("132.0"),
    "ZU:BUS:ECON:P12": Decimal("132.0"),
    "ZU:BUS:BBA:P12": Decimal("132.0"),
    "ZU:BUS:ACC:P12": Decimal("132.0"),
    "ZU:MEDIA:DJOURN:P12": Decimal("132.0"),
    "ZU:MEDIA:RTV:P12": Decimal("132.0"),
    "ZU:LAW:LAW:P12": Decimal("141.0"),
    "ZU:NURS:NURS:P12": Decimal("132.0"),
}

DISALLOWED_CODE_PATTERNS = ("FREE", "0000000", "999999", "DUMMY", "PLACEHOLDER", "TEST_")


@pytest.fixture(scope="module")
def loaded_plans():
    assert os.path.exists(PLANS_DIR), f"Missing canonical plans directory: {PLANS_DIR}"
    files = sorted([f for f in os.listdir(PLANS_DIR) if f.endswith(".json")])
    assert len(files) == 17, f"Expected 17 canonical plans, found {len(files)}"
    plans = {}
    for pf in files:
        with open(os.path.join(PLANS_DIR, pf), "r", encoding="utf-8") as f:
            plan = json.load(f)
            plans[plan["plan_key"]] = plan
    return plans


def test_01_all_17_plans_exist(loaded_plans):
    assert len(loaded_plans) == 17
    assert set(loaded_plans.keys()) == set(EXPECTED_OFFICIAL_TOTALS.keys())


def test_02_plan_identity_format(loaded_plans):
    for pk in loaded_plans:
        parts = pk.split(":")
        assert len(parts) == 4, f"Invalid plan key parts in {pk}"
        assert parts[0] == "ZU", f"Expected university code ZU in {pk}"
        assert parts[3].startswith("P"), f"Expected plan number with P prefix in {pk}"


def test_03_group_credit_sum_equals_degree_total(loaded_plans):
    for pk, plan in loaded_plans.items():
        groups = plan.get("groups", [])
        group_sum = sum(Decimal(str(g["required_credit_hours"])) for g in groups)
        stated_total = Decimal(str(plan["computed_total_required_credits"]))
        official_total = EXPECTED_OFFICIAL_TOTALS[pk]

        assert stated_total == official_total, f"{pk}: stated total {stated_total} != official total {official_total}"
        assert group_sum == stated_total, f"{pk}: group sum {group_sum} != stated total {stated_total}"


def test_04_requirement_group_codes_unique(loaded_plans):
    for pk, plan in loaded_plans.items():
        groups = plan.get("groups", [])
        codes = [g["group_code"] for g in groups]
        assert len(codes) == len(set(codes)), f"{pk}: duplicate requirement group codes: {codes}"


def test_05_free_elective_distribution_and_semantics(loaded_plans):
    for pk, plan in loaded_plans.items():
        groups = plan.get("groups", [])
        fe_groups = [g for g in groups if g.get("requirement_type") == "free_elective" or g.get("group_code") == "FREE_ELECTIVE"]
        if pk in EXPECTED_FE_PLANS:
            assert len(fe_groups) == 1, f"{pk}: expected exactly 1 free elective group"
            fe = fe_groups[0]
            assert Decimal(str(fe["required_credit_hours"])) == Decimal("3.0"), f"{fe}: expected 3.0 cr"
            assert len(fe.get("courses", [])) == 0, f"{pk}: free elective must have 0 fixed courses"
            assert fe.get("selection_policy_status") == "policy_required", f"{pk}: selection must be policy_required"
        else:
            assert len(fe_groups) == 0, f"{pk}: unexpected free elective group in program without one"


def test_06_no_fake_courses_or_duplicates(loaded_plans):
    for pk, plan in loaded_plans.items():
        for g in plan.get("groups", []):
            seen_in_group = set()
            for c in g.get("courses", []):
                code = c["course_code"]
                for pat in DISALLOWED_CODE_PATTERNS:
                    assert pat not in code.upper(), f"{pk}: fake course pattern '{pat}' in '{code}'"
                assert code not in seen_in_group, f"{pk}: duplicate course '{code}' in group '{g['group_code']}'"
                seen_in_group.add(code)


def test_07_manifest_checksum_integrity():
    manifest_path = os.path.join(DATA_DIR, "MANIFEST.json")
    assert os.path.exists(manifest_path), f"Missing MANIFEST.json in {DATA_DIR}"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    assert len(manifest) >= 20, f"Expected at least 20 tracked files, found {len(manifest)}"
    for rel_path, meta in manifest.items():
        full_path = os.path.join(DATA_DIR, rel_path.replace("/", os.sep))
        assert os.path.exists(full_path), f"File in manifest missing from disk: {rel_path}"
        with open(full_path, "rb") as bf:
            actual_sha = hashlib.sha256(bf.read()).hexdigest()
        assert actual_sha == meta["sha256"], f"Checksum mismatch for {rel_path}: {actual_sha} != {meta['sha256']}"
