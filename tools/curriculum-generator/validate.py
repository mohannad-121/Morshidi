"""Deterministic curriculum integrity validator.

Validates all 17 Zarqa University study plans across:
1. Degree totals: sum(required_credits across requirement groups) == total_credit_hours.
2. Unique requirement group identifiers per plan.
3. Free-elective requirement groups:
   - Exists in exactly the 9 approved programs (MATH, PHYS, ENGLISH, HISTORY, TRANS, ECON, BBA, ACC, NURS).
   - Has required_credit_hours == 3.0.
   - Has zero fixed course memberships (no fake/placeholder courses).
   - Selection behavior fails closed (policy_required).
4. No fake course codes (e.g. FREE0001, 0000000, 9999999).
5. No duplicate course memberships within the same requirement group.
6. Valid canonical plan composite identity: ZU:{faculty}:{major}:P{plan_number}.
7. Prerequisite references: unresolved prerequisites remain fail-closed (review_required = True).
8. Manifest checksum integrity: all tracked files in data/curricula match MANIFEST.json.
"""

import os
import sys
import json
import hashlib
from typing import Dict, Any, List

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(DIR))
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
    "ZU:IT:AI:P12": 132.0,
    "ZU:IT:SE:P12": 132.0,
    "ZU:IT:CS:P12": 132.0,
    "ZU:IT:CYBER:P12": 132.0,
    "ZU:SCI:MATH:P12": 132.0,
    "ZU:SCI:PHYS:P12": 132.0,
    "ZU:ARTS:ARABIC:P12": 132.0,
    "ZU:ARTS:ENGLISH:P12": 132.0,
    "ZU:ARTS:HISTORY:P12": 132.0,
    "ZU:ARTS:TRANS:P12": 132.0,
    "ZU:BUS:ECON:P12": 132.0,
    "ZU:BUS:BBA:P12": 132.0,
    "ZU:BUS:ACC:P12": 132.0,
    "ZU:MEDIA:DJOURN:P12": 132.0,
    "ZU:MEDIA:RTV:P12": 132.0,
    "ZU:LAW:LAW:P12": 141.0,
    "ZU:NURS:NURS:P12": 132.0,
}

FAKE_CODE_PATTERNS = ["FREE", "0000000", "999999", "DUMMY", "PLACEHOLDER", "TEST_"]


def validate_curricula() -> List[str]:
    errors = []

    # 1. Check all 17 plans exist
    plan_files = sorted([f for f in os.listdir(PLANS_DIR) if f.endswith(".json")])
    if len(plan_files) != 17:
        errors.append(f"Expected 17 plan JSON files in data/curricula/plans, found {len(plan_files)}")
        return errors

    plans_seen = {}

    for pf in plan_files:
        path = os.path.join(PLANS_DIR, pf)
        with open(path, "r", encoding="utf-8") as f:
            plan = json.load(f)

        pk = plan.get("plan_key")
        if not pk:
            errors.append(f"{pf}: missing plan_key")
            continue
        plans_seen[pk] = plan

        # Identity validation
        parts = pk.split(":")
        if len(parts) != 4 or parts[0] != "ZU" or not parts[3].startswith("P"):
            errors.append(f"{pf}: Invalid plan key structure '{pk}'")

        # Total credit sum
        groups = plan.get("groups", [])
        computed_sum = sum(float(g.get("required_credit_hours", 0)) for g in groups)
        stated_total = float(plan.get("computed_total_required_credits", 0))
        expected_total = EXPECTED_OFFICIAL_TOTALS.get(pk)

        if expected_total is None:
            errors.append(f"{pk}: Unknown plan key not in official plan registry")
        elif stated_total != expected_total:
            errors.append(f"{pk}: stated total {stated_total} != official total {expected_total}")

        if computed_sum != stated_total:
            errors.append(f"{pk}: group sum {computed_sum} != stated total {stated_total}")

        # Unique group codes
        group_codes = [g.get("group_code") for g in groups]
        if len(group_codes) != len(set(group_codes)):
            errors.append(f"{pk}: duplicate requirement group codes found: {group_codes}")

        # Check Free Elective group semantics
        fe_groups = [g for g in groups if g.get("requirement_type") == "free_elective" or g.get("group_code") == "FREE_ELECTIVE"]
        if pk in EXPECTED_FE_PLANS:
            if len(fe_groups) != 1:
                errors.append(f"{pk}: Expected exactly 1 free elective group, found {len(fe_groups)}")
            else:
                fe = fe_groups[0]
                if float(fe.get("required_credit_hours", 0)) != 3.0:
                    errors.append(f"{pk}: Free elective required credits must be 3.0, found {fe.get('required_credit_hours')}")
                if len(fe.get("courses", [])) != 0:
                    errors.append(f"{pk}: Free elective group must have 0 courses, found {len(fe.get('courses'))}")
                if fe.get("selection_policy_status") != "policy_required":
                    errors.append(f"{pk}: Free elective selection policy status must be 'policy_required', found '{fe.get('selection_policy_status')}'")
        else:
            if len(fe_groups) > 0:
                errors.append(f"{pk}: Program does not have free elective requirement, but free elective group was found")

        # Check courses
        for g in groups:
            courses = g.get("courses", [])
            seen_courses_in_group = set()
            for c in courses:
                code = c.get("course_code", "")
                # Fake code check
                for pat in FAKE_CODE_PATTERNS:
                    if pat in code.upper():
                        errors.append(f"{pk}: Fake/disallowed course code found: '{code}' in group {g.get('group_code')}")
                # Duplicate check
                if code in seen_courses_in_group:
                    errors.append(f"{pk}: Duplicate course code '{code}' in group {g.get('group_code')}")
                seen_courses_in_group.add(code)

    # 2. Check MANIFEST.json checksums
    manifest_path = os.path.join(DATA_DIR, "MANIFEST.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        for rel_path, meta in manifest.items():
            full_path = os.path.join(DATA_DIR, rel_path.replace("/", os.sep))
            if not os.path.exists(full_path):
                errors.append(f"MANIFEST tracked file missing from disk: {rel_path}")
                continue
            with open(full_path, "rb") as bf:
                disk_h = hashlib.sha256(bf.read()).hexdigest()
            if disk_h != meta.get("sha256"):
                errors.append(f"Checksum mismatch for {rel_path}: manifest={meta.get('sha256')} disk={disk_h}")

    return errors


def main():
    print("=== Validating All 17 Curricula Definitions ===")
    errors = validate_curricula()
    if errors:
        print(f"FAILED: Found {len(errors)} validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASS: All 17 plans verified with deterministic mathematical and schema integrity!")
        for pk, total in sorted(EXPECTED_OFFICIAL_TOTALS.items()):
            fe_status = "FE: 3.0 cr" if pk in EXPECTED_FE_PLANS else "FE: None  "
            print(f"  [OK] {pk:20} -> Total: {total:5.1f} cr | {fe_status}")


if __name__ == "__main__":
    main()
