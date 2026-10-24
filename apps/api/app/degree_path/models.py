"""Immutable domain models and contracts for the deterministic degree path planning engine (Phase 9.2).

No FastAPI, Starlette, Supabase, httpx, or I/O dependency is permitted in this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from hashlib import sha256

from app.planner.models import SemesterPlanOption

# ---------------------------------------------------------------------------
# Policy Constants
# ---------------------------------------------------------------------------

DEGREE_PATH_POLICY_VERSION = "1.0"
PLANNING_SCOPE = "MODELED_DEGREE_PATH_ONLY"
DEFAULT_BEAM_WIDTH = 3
DEFAULT_SEMESTER_BRANCH_WIDTH = 3
DEFAULT_CANDIDATE_WINDOW_SIZE = 15
DEFAULT_COMBINATION_EVALUATION_LIMIT = 256
MAX_CREDIT_HOURS_SAFETY_CEILING = Decimal("30.00")

# ---------------------------------------------------------------------------
# Domain Exceptions
# ---------------------------------------------------------------------------


class DegreePathConstraintError(ValueError):
    """Raised when user planning constraints fail validation."""


class DegreePathIntegrityError(RuntimeError):
    """Raised when input catalogs, student history, or search transitions violate integrity invariants."""


class DegreePathValidationErrorCode(str, Enum):
    """Stable fail-closed codes emitted by the final path validator."""

    CREDIT_TOTAL_MISMATCH = "CREDIT_TOTAL_MISMATCH"
    DUPLICATE_COURSE = "DUPLICATE_COURSE"
    FOREIGN_PLAN_COURSE = "FOREIGN_PLAN_COURSE"
    MISSING_PLAN_COURSE = "MISSING_PLAN_COURSE"
    PREREQUISITE_ORDER_VIOLATION = "PREREQUISITE_ORDER_VIOLATION"
    UNRESOLVED_DEPENDENCY = "UNRESOLVED_DEPENDENCY"
    COMPLETED_COURSE_REPLACED = "COMPLETED_COURSE_REPLACED"
    INVALID_TERM_LOAD = "INVALID_TERM_LOAD"
    RESULT_MISMATCH = "RESULT_MISMATCH"


class DegreePathValidationError(DegreePathIntegrityError):
    """A generated path failed deterministic post-search validation."""

    def __init__(self, code: DegreePathValidationErrorCode, detail: str) -> None:
        self.code = code
        super().__init__(f"{code.value}: {detail}")


class DegreePathComputationTimeout(RuntimeError):
    """Raised when a bounded degree-path calculation expires or is cancelled."""


class DegreePathCapacityError(RuntimeError):
    """Raised when this worker is already calculating a degree path."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PathStatus(str, Enum):
    """Academic reason why deterministic degree path expansion stopped."""

    MODELED_COMPLETE = "MODELED_COMPLETE"
    """All modeled study plan requirements are satisfied under simulation."""

    HORIZON_REACHED = "HORIZON_REACHED"
    """The path reached max_semesters_ahead without fully satisfying all requirements."""

    BLOCKED_BY_REVIEW_REQUIRED = "BLOCKED_BY_REVIEW_REQUIRED"
    """When depth < max_semesters_ahead: remaining modeled requirements include prerequisite logic requiring review."""

    BLOCKED_BY_CURRENT_IN_PROGRESS = "BLOCKED_BY_CURRENT_IN_PROGRESS"
    """When depth < max_semesters_ahead: remaining courses cannot be planned because they depend on an active in-progress course."""

    NO_VALID_NEXT_PLAN = "NO_VALID_NEXT_PLAN"
    """When depth < max_semesters_ahead: no valid semester plan combination could be formed under constraints."""


class BlockerType(str, Enum):
    """Diagnostic codes describing unresolved academic conditions in final states."""

    REVIEW_REQUIRED_BLOCKER = "REVIEW_REQUIRED_BLOCKER"
    """Remaining required courses have unresolved or source-conflict prerequisite logic requiring review."""

    CURRENT_IN_PROGRESS_BLOCKER = "CURRENT_IN_PROGRESS_BLOCKER"
    """A remaining modeled requirement is currently IN_PROGRESS and unresolved."""

    PREREQUISITES_LOCKED = "PREREQUISITES_LOCKED"
    """A relevant remaining requirement has a Phase 5 missing-prerequisite decision."""

    PLAN_CONSTRAINTS_TOO_RESTRICTIVE = "PLAN_CONSTRAINTS_TOO_RESTRICTIVE"
    """Requested credit hours or course limits prevent selecting remaining eligible courses."""

    CANDIDATE_WINDOW_EXCLUSION = "CANDIDATE_WINDOW_EXCLUSION"
    """An outside-window recommendation fits constraints when top-M yields no plan."""


class UnplacedCreditReason(str, Enum):
    """Deterministic, non-overlapping explanation for an unplaced requirement."""

    FREE_ELECTIVE_POLICY_REQUIRED = "FREE_ELECTIVE_POLICY_REQUIRED"
    UNSCHEDULED_REQUIRED_CREDITS = "UNSCHEDULED_REQUIRED_CREDITS"
    UNSCHEDULED_ELECTIVE_CREDITS = "UNSCHEDULED_ELECTIVE_CREDITS"
    MANDATORY_ZERO_CREDIT_REQUIREMENT = "MANDATORY_ZERO_CREDIT_REQUIREMENT"
    UNMODELED_PLAN_CREDITS = "UNMODELED_PLAN_CREDITS"


class PathReasonCode(str, Enum):
    """Stable, machine-readable reason codes for generated degree paths."""

    REACHES_MODELED_PLAN_COMPLETION = "REACHES_MODELED_PLAN_COMPLETION"
    """Path successfully satisfies all modeled study plan requirements under simulation."""

    FEWER_MODELED_SEMESTERS = "FEWER_MODELED_SEMESTERS"
    """Path achieves completion in fewer modeled semesters than competing valid paths."""

    MAXIMIZES_PROGRESS_WITHIN_HORIZON = "MAXIMIZES_PROGRESS_WITHIN_HORIZON"
    """Path achieves the maximal credit and requirement progress within the planning horizon."""

    CONTAINS_MANDATORY_COURSES = "CONTAINS_MANDATORY_COURSES"
    """Path incorporates mandatory study plan courses in its planned semesters."""

    INCLUDES_ZERO_CREDIT_REQUIRED = "INCLUDES_ZERO_CREDIT_REQUIRED"
    """Path schedules required zero-credit courses (e.g. 0200115, 1509999)."""

    COMPLETES_ALL_REQUIREMENT_GROUPS = "COMPLETES_ALL_REQUIREMENT_GROUPS"
    """Path satisfies 100% of the study plan requirement groups."""

    INCLUDES_PREVIOUSLY_ATTEMPTED_COURSE = "INCLUDES_PREVIOUSLY_ATTEMPTED_COURSE"
    """Path includes at least one course previously attempted but not passed."""

    BLOCKED_BY_REVIEW_REQUIRED = "BLOCKED_BY_REVIEW_REQUIRED"
    """Further path progression halted due to courses requiring academic review."""

    BLOCKED_BY_CURRENT_IN_PROGRESS = "BLOCKED_BY_CURRENT_IN_PROGRESS"
    """Path progression halted because remaining courses depend on an active in-progress attempt."""

    NO_VALID_NEXT_SEMESTER = "NO_VALID_NEXT_SEMESTER"
    """Path halted because no valid course combination could be formed under constraints."""


# ---------------------------------------------------------------------------
# Constraints Model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DegreePathConstraints:
    """Immutable user planning preferences and presentation constraints."""

    max_credit_hours_per_semester: Decimal
    max_courses_per_semester: int | None = None
    max_semesters_ahead: int = 8
    max_paths: int = 3
    multi_strategy: bool = False

    def __post_init__(self) -> None:
        # Validate max_credit_hours_per_semester
        raw_credits = self.max_credit_hours_per_semester
        if isinstance(raw_credits, bool):
            raise DegreePathConstraintError("max_credit_hours_per_semester cannot be a boolean")
        if isinstance(raw_credits, float):
            raise DegreePathConstraintError(
                "max_credit_hours_per_semester must be a Decimal, string, or integer, not float"
            )
        try:
            if isinstance(raw_credits, int):
                dec_val = Decimal(str(raw_credits))
            elif isinstance(raw_credits, Decimal):
                dec_val = raw_credits
            elif isinstance(raw_credits, str):
                dec_val = Decimal(raw_credits)
            else:
                raise DegreePathConstraintError(
                    f"Unsupported type for max_credit_hours_per_semester: {type(raw_credits)}"
                )
        except DegreePathConstraintError:
            raise
        except Exception as exc:
            raise DegreePathConstraintError(f"Invalid max_credit_hours_per_semester: {exc}") from exc

        if dec_val.is_nan() or dec_val.is_infinite():
            raise DegreePathConstraintError("max_credit_hours_per_semester must be a finite number")
        if dec_val < Decimal("0"):
            raise DegreePathConstraintError("max_credit_hours_per_semester cannot be negative")
        if dec_val > MAX_CREDIT_HOURS_SAFETY_CEILING:
            raise DegreePathConstraintError(
                f"max_credit_hours_per_semester cannot exceed safety limit of {MAX_CREDIT_HOURS_SAFETY_CEILING}"
            )
        object.__setattr__(self, "max_credit_hours_per_semester", dec_val)

        # Validate max_courses_per_semester
        if self.max_courses_per_semester is not None:
            if isinstance(self.max_courses_per_semester, bool) or not isinstance(
                self.max_courses_per_semester, int
            ):
                raise DegreePathConstraintError("max_courses_per_semester must be an integer or None")
            if self.max_courses_per_semester < 1 or self.max_courses_per_semester > 10:
                raise DegreePathConstraintError("max_courses_per_semester must be between 1 and 10")

        # Validate max_semesters_ahead
        if isinstance(self.max_semesters_ahead, bool) or not isinstance(self.max_semesters_ahead, int):
            raise DegreePathConstraintError("max_semesters_ahead must be an integer")
        if self.max_semesters_ahead < 1 or self.max_semesters_ahead > 16:
            raise DegreePathConstraintError("max_semesters_ahead must be between 1 and 16")

        # Validate max_paths
        if isinstance(self.max_paths, bool) or not isinstance(self.max_paths, int):
            raise DegreePathConstraintError("max_paths must be an integer")
        if self.max_paths < 1 or self.max_paths > 10:
            raise DegreePathConstraintError("max_paths must be between 1 and 10")

        # Validate multi_strategy
        if not isinstance(self.multi_strategy, bool):
            raise DegreePathConstraintError("multi_strategy must be a boolean")


class DegreePathStrategy(str, Enum):
    """Academic planning strategies for degree path generation."""

    FASTEST = "FASTEST"
    BALANCED = "BALANCED"
    LIGHTER = "LIGHTER"


STRATEGY_LABELS_AR: dict[str, str] = {
    DegreePathStrategy.FASTEST.value: "الأسرع للتخرج",
    DegreePathStrategy.BALANCED.value: "الأكثر توازناً",
    DegreePathStrategy.LIGHTER.value: "الأخف دراسياً",
}


# ---------------------------------------------------------------------------
# Result Domain Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModeledSemesterEntry:
    """A single modeled semester within a multi-semester degree path."""

    semester_index: int
    plan_option: SemesterPlanOption
    completed_plan_credits_after: Decimal
    remaining_plan_credits_after: Decimal
    newly_satisfied_requirement_group_codes: tuple[str, ...]


def deterministic_path_id(
    study_plan_id: str,
    semesters: tuple[ModeledSemesterEntry, ...],
) -> str:
    """Return a stable identity for one exact semester/course allocation."""
    allocation = "|".join(
        f"{semester.semester_index}:" + ",".join(
            course.course_code for course in semester.plan_option.courses
        )
        for semester in semesters
    )
    digest = sha256(f"{study_plan_id}|{allocation}".encode("utf-8")).hexdigest()
    return f"dp_{digest[:24]}"


@dataclass(frozen=True)
class DegreePathCreditSummary:
    """Canonical credit accounting for one candidate path."""

    degree_required_credits: Decimal
    completed_credits: Decimal
    current_credits: Decimal
    future_placed_credits: Decimal
    unplaced_credits: Decimal


@dataclass(frozen=True)
class DegreePathFreeElectiveRequirement:
    """A credit requirement, never a fabricated catalog course or section."""

    group_code: str
    name_ar: str
    name_en: str | None
    required_credits: Decimal
    completed_credits: Decimal
    current_credits: Decimal
    remaining_credits_after_current: Decimal
    selection_state: str
    completed_course_codes: tuple[str, ...]
    current_course_codes: tuple[str, ...]


@dataclass(frozen=True)
class UnplacedCreditBreakdown:
    """One requirement-group contribution to the aggregate unplaced total."""

    reason: UnplacedCreditReason
    credits: Decimal
    requirement_group_code: str
    course_codes: tuple[str, ...]
    evidence_codes: tuple[str, ...]
    actionable: bool


@dataclass(frozen=True)
class DegreePathOption:
    """A complete ranked multi-semester degree path option."""

    path_id: str
    rank: int
    status: PathStatus
    semesters: tuple[ModeledSemesterEntry, ...]
    semester_count: int
    total_planned_courses: int
    total_planned_credits: Decimal
    completed_plan_credit_delta: Decimal
    final_completed_plan_credits: Decimal
    final_remaining_plan_credits: Decimal
    newly_satisfied_requirement_group_count: int
    newly_satisfied_requirement_group_codes: tuple[str, ...]
    remaining_required_course_codes: tuple[str, ...]
    unresolved_blocker_codes: tuple[str, ...]
    aggregate_semester_rank_sum: int
    priority_tuple: tuple[int, int, Decimal, int, int, int, tuple[tuple[str, ...], ...]]
    reason_codes: tuple[PathReasonCode, ...]
    completed_course_codes: tuple[str, ...]
    current_course_codes: tuple[str, ...]
    unplaced_course_codes: tuple[str, ...]
    credit_summary: DegreePathCreditSummary
    free_elective_requirements: tuple[DegreePathFreeElectiveRequirement, ...] = ()
    unplaced_credit_breakdown: tuple[UnplacedCreditBreakdown, ...] = ()
    strategy: str = DegreePathStrategy.FASTEST.value
    strategy_name_ar: str = "الأسرع للتخرج"


def canonical_semantic_fingerprint(
    option: DegreePathOption,
) -> tuple[tuple[tuple[str, ...], ...], tuple[Decimal, ...], tuple[str, ...]]:
    """Return the canonical semantic signature for a degree path option.

    Two paths with the same semester count, same sorted course codes in each semester,
    same semester credit distribution, and same unplaced requirements have the same
    academic allocation.
    """
    semesters_courses = tuple(
        tuple(sorted(course.course_code for course in semester.plan_option.courses))
        for semester in option.semesters
    )
    semester_credits = tuple(semester.plan_option.total_credit_hours for semester in option.semesters)
    unplaced_reqs = tuple(sorted(req.group_code for req in option.free_elective_requirements))
    return (semesters_courses, semester_credits, unplaced_reqs)


def are_paths_materially_distinct(
    path1: DegreePathOption,
    path2: DegreePathOption,
) -> bool:
    """Two candidate paths are materially distinct IF AND ONLY IF:
    - different semester count
    OR
    - different semester credit distribution
    OR
    - at least one course is placed in a different semester
    OR
    - different elective / requirement sequencing

    They are NOT materially distinct if they only differ by:
    - candidate ID / path_id
    - internal array ordering within the same semester
    - identical semesters with identical courses
    """
    if path1.semester_count != path2.semester_count:
        return True

    credits1 = tuple(s.plan_option.total_credit_hours for s in path1.semesters)
    credits2 = tuple(s.plan_option.total_credit_hours for s in path2.semesters)
    if credits1 != credits2:
        return True

    placements1: dict[str, int] = {}
    for sem in path1.semesters:
        for c in sem.plan_option.courses:
            placements1[c.course_code] = sem.semester_index

    placements2: dict[str, int] = {}
    for sem in path2.semesters:
        for c in sem.plan_option.courses:
            placements2[c.course_code] = sem.semester_index

    common_courses = set(placements1.keys()) & set(placements2.keys())
    if not common_courses and (placements1 or placements2):
        return True

    for code in common_courses:
        if placements1[code] != placements2[code]:
            return True

    all_codes1 = set(placements1.keys())
    all_codes2 = set(placements2.keys())
    if all_codes1 != all_codes2:
        return False

    return False


def deduplicate_candidate_paths(
    options: list[DegreePathOption],
) -> list[DegreePathOption]:
    """Deduplicate candidate paths to ensure all returned paths are materially distinct.

    Preserves ranking order, retaining the highest-ranked candidate among duplicates.
    """
    unique: list[DegreePathOption] = []
    seen_fingerprints: set[tuple] = set()

    for opt in options:
        fp = canonical_semantic_fingerprint(opt)
        if fp in seen_fingerprints:
            continue
        is_distinct = True
        for existing in unique:
            if not are_paths_materially_distinct(existing, opt):
                is_distinct = False
                break
        if is_distinct:
            seen_fingerprints.add(fp)
            unique.append(opt)

    return unique



@dataclass(frozen=True)
class DegreePathResult:
    """Complete deterministic result returned by the degree path planning engine."""

    study_plan_id: str
    degree_path_policy_version: str
    planning_scope: str
    constraints: DegreePathConstraints
    paths: tuple[DegreePathOption, ...]
    initial_completed_credits: Decimal
    initial_remaining_credits: Decimal
    initial_satisfied_group_count: int
    total_requirement_group_count: int
    unresolved_review_required_courses: tuple[str, ...] = ()
    persisted_in_progress_courses: tuple[str, ...] = ()
    total_parent_states_expanded: int = 0
    methodology_note: str = ""
    limitations: tuple[str, ...] = ()
