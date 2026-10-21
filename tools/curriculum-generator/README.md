# Zarqa University Curriculum Generator & Canonical Definitions

## Overview

This directory contains the authoritative, deterministic curriculum generator for all 17 Zarqa University study plans supported in Morshidi and Fake University.

## Architecture: Source vs Generated Artifacts

### 1. Source (in `tools/curriculum-generator/`)
- `it_science.py`: Canonical course tables and requirement groups for Faculty of IT (SE, CS, CYBER) and Faculty of Science (MATH, PHYS).
- `arts_business.py`: Canonical course tables and requirement groups for Faculty of Arts (ARABIC, ENGLISH, HISTORY, TRANS) and Faculty of Business (ECON, BBA, ACC).
- `media_law_nursing.py`: Canonical course tables and requirement groups for Faculty of Media (DJOURN, RTV), Faculty of Law (LAW), and Faculty of Nursing (NURS).
- `common.py`: Shared university requirement helper tuples (`UNI_REQ`, `UNI_ELECT_GENERAL`, `UNI_ELECT_IT`, `UNI_ELECT_NURSING`) and course builder function `c()`.
- `build.py`: Deterministic build engine synthesizing plan structures, computing group credit sums, catalog uniqueness, prerequisite graph metadata, and emitting canonical files.
- `generate_morshidi_sql.py`: Generates the Morshidi PostgreSQL catalog seed and deterministic UUID mapping.
- `generate_fake_university.py`: Generates the Fake University migration SQL and plan-aware registry JSON.
- `regenerate_all.py`: Single master runner executing all build steps and recalculating `MANIFEST.json`.
- `validate.py`: Independent CLI validator enforcing credit equation, unique IDs, fail-closed free elective semantics, and checksum integrity.

### 2. Generated Authoritative Artifacts (in `data/curricula/`)
- `plans/`: 17 canonical JSON plan definitions (`ZU_IT_AI_P12.json` through `ZU_SCI_PHYS_P12.json`).
- `canonical_curriculum.json`: Master curriculum registry combining all 17 plans.
- `courses.csv`: Unique university courses with catalog status (`known` / `referenced_only`).
- `plan_courses.csv`: Plan-to-course memberships with prerequisite logic status and review flags.
- `plans.csv`: Program summary table with faculties, majors, plan numbers, and credit totals.
- `morshidi_plan_ids.json`: Deterministic UUIDs for all 17 plans.
- `morshidi_multi_plan_seed.sql`: PostgreSQL seed script for Morshidi.
- `fake_university_curriculum_registry.json`: JSON curriculum registry for Fake University SIS.
- `fake_university_multi_plan_migration.sql`: Dedicated plan-aware curriculum DDL & DML for Fake University.
- `MANIFEST.json`: Cryptographic SHA-256 checksums and byte sizes for all tracked artifacts.

## Academic Invariants Enforced

1. **Credit Equation**: For all 17 plans, `sum(required_credit_hours across requirement groups) == total_credit_hours`.
   - 16 Bachelor programs: 132.0 credit hours.
   - Law program: 141.0 credit hours.
2. **Governed Free Elective**: Exactly 9 programs require a 3-credit Free Elective (`FREE_ELECTIVE`, "متطلب حر"):
   - `ZU:SCI:MATH:P12`, `ZU:SCI:PHYS:P12`
   - `ZU:ARTS:ENGLISH:P12`, `ZU:ARTS:HISTORY:P12`, `ZU:ARTS:TRANS:P12`
   - `ZU:BUS:ECON:P12`, `ZU:BUS:BBA:P12`, `ZU:BUS:ACC:P12`
   - `ZU:NURS:NURS:P12`
3. **No Fake Courses**: Free Elective groups contain ZERO fixed course memberships (`len(courses) == 0`). No placeholder codes (e.g. `FREE0001`, `0000000`, `9999999`) exist.
4. **Fail-Closed Selection**: `selection_policy = 'university_approved'`, `selection_policy_status = 'policy_required'`. Real courses cannot be selected until the university supplies an authoritative eligibility mapping.
5. **Deterministic Plan Identity**: `ZU:{faculty_code}:{major_code}:P{plan_number}`.

## Regeneration Instructions

To regenerate all curriculum artifacts deterministically:

```bash
# 1. Run master build pipeline
python tools/curriculum-generator/regenerate_all.py

# 2. Run CLI integrity validation
python tools/curriculum-generator/validate.py

# 3. Run CI test suite
pytest apps/api/tests/test_curriculum_integrity.py -v
```
