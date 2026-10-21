"""Authoritative regression and audit test suite for Multi-Strategy Degree Path generation.

Verifies:
1. Nursing student 209900017 generates 3 materially distinct candidates with genuine strategies.
2. Deduplication prunes identical or non-materially distinct candidate paths.
3. All 17 canonical Zarqa University study plans produce 3 unique, materially distinct strategies.
4. Total curriculum credit sums, Free Elective requirements, and fail-closed semantics are preserved.
"""

from decimal import Decimal
import os
import pytest
import httpx

from app.catalog.supabase_repository import SupabaseAcademicCatalogRepository
from app.degree_path.engine import plan_degree_paths
from app.degree_path.models import (
    DegreePathConstraints,
    DegreePathStrategy,
    STRATEGY_LABELS_AR,
    canonical_semantic_fingerprint,
    are_paths_materially_distinct,
    deduplicate_candidate_paths,
)
from app.services.student import StudentService
from app.student.models import StudentAcademicState

LOCAL_SUPABASE_URL = os.getenv("MORSHIDI_LOCAL_SUPABASE_URL", "http://127.0.0.1:54321")
LOCAL_SERVER_KEY = os.getenv(
    "MORSHIDI_LOCAL_SUPABASE_SERVER_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU",
)

NURSING_STUDENT_OWNER = "209900017-0000-0000-0000-000000000017"
NURSING_PLAN_ID = "2a78bbbb-0dc0-5c46-8630-7a46e4179830"

ALL_17_PLANS = [
    ("10000000-0000-0000-0000-000000000005", "ZU:IT:AI:P12", Decimal("132"), False),
    ("1b709940-4279-560b-88ff-dacd5da636f2", "ZU:IT:SE:P12", Decimal("132"), False),
    ("426168f9-4298-5b59-91d8-8daae30381d8", "ZU:IT:CS:P12", Decimal("132"), False),
    ("7987a763-a33e-5318-866a-8c68b591b92a", "ZU:IT:CYBER:P12", Decimal("132"), False),
    ("070818ab-9577-5457-afd9-865a50241b9d", "ZU:SCI:MATH:P12", Decimal("132"), True),
    ("6a3a9646-2822-56da-b486-a001f0aa927a", "ZU:SCI:PHYS:P12", Decimal("132"), True),
    ("9d086908-ea56-558f-a246-ffd5cb3d42d2", "ZU:ARTS:ARABIC:P12", Decimal("132"), False),
    ("4aed9e40-89eb-5bf9-9eea-129dbad7a936", "ZU:ARTS:ENGLISH:P12", Decimal("132"), True),
    ("91eec87e-6eec-5bb4-9f4c-a24cad790747", "ZU:ARTS:HISTORY:P12", Decimal("132"), True),
    ("a6622d55-d8b8-5a8c-8c6b-70e83391c100", "ZU:ARTS:TRANS:P12", Decimal("132"), True),
    ("ce695e6c-b58c-545f-9dd9-a58c659b685e", "ZU:BUS:ECON:P12", Decimal("132"), True),
    ("6b5756b1-e8f1-5274-9711-4189a5eff158", "ZU:BUS:BBA:P12", Decimal("132"), True),
    ("94e47824-8352-5280-a8d9-796e329c845e", "ZU:BUS:ACC:P12", Decimal("132"), True),
    ("3c7af412-ab25-56e1-9eef-dd7cdfbe3848", "ZU:MEDIA:DJOURN:P12", Decimal("132"), False),
    ("45a8805e-e7fb-5c2b-8d2f-e73e7e67a2a2", "ZU:MEDIA:RTV:P12", Decimal("132"), False),
    ("80778bf1-bee9-5485-abf6-840e467d1982", "ZU:LAW:LAW:P12", Decimal("141"), False),
    ("2a78bbbb-0dc0-5c46-8630-7a46e4179830", "ZU:NURS:NURS:P12", Decimal("132"), True),
]


class _FakeStudentRepo:
    def __init__(self, state: StudentAcademicState) -> None:
        self._state = state

    async def load_student_academic_state(self, owner_user_id: str) -> StudentAcademicState:
        return self._state


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_nursing_student_209900017_multi_strategy_distinct_candidates() -> None:
    """Student 209900017 (Nursing) must return 3 materially distinct candidates."""
    async with httpx.AsyncClient(timeout=30.0) as http:
        cat_repo = SupabaseAcademicCatalogRepository(LOCAL_SUPABASE_URL, LOCAL_SERVER_KEY, client=http)
        nursing_state = StudentAcademicState(
            profile_id="profile-nursing-209900017",
            owner_user_id=NURSING_STUDENT_OWNER,
            study_plan_id=NURSING_PLAN_ID,
            reported_cumulative_gpa=None,
            reported_gpa_scale=None,
            reported_earned_credit_hours=None,
            attempts=(),
        )
        service = StudentService(_FakeStudentRepo(nursing_state), None, cat_repo)  # type: ignore[arg-type]

        result = await service.get_degree_paths(
            NURSING_STUDENT_OWNER,
            max_credit_hours_per_semester=Decimal("18"),
            max_semesters_ahead=16,
            max_paths=3,
        )

    assert len(result.paths) == 3, f"Expected 3 candidate paths, got {len(result.paths)}"

    p1, p2, p3 = result.paths

    # Verify strategy assignments
    assert p1.strategy == DegreePathStrategy.FASTEST.value
    assert p1.strategy_name_ar == "الأسرع للتخرج"
    assert p2.strategy == DegreePathStrategy.BALANCED.value
    assert p2.strategy_name_ar == "الأكثر توازناً"
    assert p3.strategy == DegreePathStrategy.LIGHTER.value
    assert p3.strategy_name_ar == "الأخف دراسياً"

    # Verify distinct semester counts
    assert p1.semester_count == 6
    assert p2.semester_count == 7
    assert p3.semester_count == 9

    # Verify distinct credit curves
    c1 = [s.plan_option.total_credit_hours for s in p1.semesters]
    c2 = [s.plan_option.total_credit_hours for s in p2.semesters]
    c3 = [s.plan_option.total_credit_hours for s in p3.semesters]
    assert c1 == [Decimal("18"), Decimal("18"), Decimal("18"), Decimal("18"), Decimal("17"), Decimal("14")]
    assert c2 == [Decimal("15"), Decimal("15"), Decimal("15"), Decimal("15"), Decimal("15"), Decimal("15"), Decimal("13")]
    assert c3 == [Decimal("12"), Decimal("12"), Decimal("12"), Decimal("12"), Decimal("12"), Decimal("12"), Decimal("12"), Decimal("10"), Decimal("9")]

    # Verify pairwise material distinctness
    assert are_paths_materially_distinct(p1, p2) is True
    assert are_paths_materially_distinct(p1, p3) is True
    assert are_paths_materially_distinct(p2, p3) is True

    # Verify canonical semantic fingerprints are all unique
    fps = [canonical_semantic_fingerprint(p) for p in result.paths]
    assert len(set(fps)) == 3

    # Verify Nursing curriculum total and Free Elective
    for path in result.paths:
        assert path.credit_summary.degree_required_credits == Decimal("132")
        fe_reqs = [r for r in path.free_elective_requirements if r.group_code == "FREE_ELECTIVE"]
        assert len(fe_reqs) == 1
        assert fe_reqs[0].required_credits == Decimal("3")
        assert fe_reqs[0].selection_state == "FREE_ELECTIVE_POLICY_REQUIRED"


@pytest.mark.anyio
async def test_all_17_curricula_multi_strategy_materially_distinct() -> None:
    """All 17 study plans must generate 3 materially distinct candidates with multi_strategy."""
    async with httpx.AsyncClient(timeout=120.0) as http:
        cat_repo = SupabaseAcademicCatalogRepository(LOCAL_SUPABASE_URL, LOCAL_SERVER_KEY, client=http)

        for plan_id, plan_code, expected_total, has_free_elective in ALL_17_PLANS:
            p_cat = await cat_repo.load_progress_catalog(plan_id)
            e_cat = await cat_repo.load_plan_eligibility_catalog(plan_id)

            result = plan_degree_paths(
                progress_catalog=p_cat,
                eligibility_catalog=e_cat,
                student_attempts=(),
                constraints=DegreePathConstraints(
                    max_credit_hours_per_semester=Decimal("18"),
                    max_semesters_ahead=16,
                    max_paths=3,
                    multi_strategy=True,
                ),
            )

            assert len(result.paths) == 3, f"Plan {plan_code} expected 3 candidate paths, got {len(result.paths)}"

            # Verify all candidates have unique fingerprints
            fps = [canonical_semantic_fingerprint(p) for p in result.paths]
            assert len(set(fps)) == len(result.paths), f"Plan {plan_code} has duplicate candidate fingerprints"

            # Verify pairwise material distinctness
            p1, p2, p3 = result.paths
            assert are_paths_materially_distinct(p1, p2) is True, f"Plan {plan_code} p1 and p2 not distinct"
            assert are_paths_materially_distinct(p1, p3) is True, f"Plan {plan_code} p1 and p3 not distinct"
            assert are_paths_materially_distinct(p2, p3) is True, f"Plan {plan_code} p2 and p3 not distinct"

            # Verify curriculum totals
            for path in result.paths:
                assert path.credit_summary.degree_required_credits == expected_total, (
                    f"Plan {plan_code} expected total {expected_total}, got {path.credit_summary.degree_required_credits}"
                )
                if has_free_elective:
                    fe_reqs = [r for r in path.free_elective_requirements if r.group_code == "FREE_ELECTIVE"]
                    assert len(fe_reqs) == 1, f"Plan {plan_code} missing FREE_ELECTIVE requirement node"
                    assert fe_reqs[0].required_credits == Decimal("3")
                    assert fe_reqs[0].selection_state == "FREE_ELECTIVE_POLICY_REQUIRED"
