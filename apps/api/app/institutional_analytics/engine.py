"""Pure deterministic institutional metrics. No LLM, I/O, or mutation."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from statistics import median

from .models import (
    AdvisorCaseload,
    AnalyticsSnapshot,
    CourseFact,
    CourseMetric,
    DashboardResponse,
    Metric,
    Overview,
    ProgramBreakdown,
    ProgramMetric,
    ProgressBand,
    ProjectionComponents,
    ReviewQueueItem,
    SimulationRequest,
    SimulationResponse,
    StudentFact,
)

PROJECTION_METHOD = (
    "Distinct student union of currently eligible, active planner-selected, and courses reachable "
    "within one verified prerequisite step; completed and currently registered courses are excluded."
)
BOTTLENECK_METHOD = (
    "Transparent 0-100 sum: required-course role 25, verified downstream impact up to 25 "
    "(5 per course), positive capacity-gap share up to 30, and affected-student share up to 20."
)
CAPACITY_METHOD = (
    "UNDER_CAPACITY <50% projected demand/capacity; HEALTHY 50-84%; NEAR_CAPACITY 85-100%; "
    "OVER_DEMAND when projected demand exceeds offered seats."
)


def _metric(value: int | float | None, unit: str, *, status: str = "AVAILABLE",
            inputs: dict | None = None, reasons: list[str] | None = None) -> Metric:
    return Metric(value=value, unit=unit, status=status, inputs=inputs or {}, reason_codes=reasons or [])


def _student_sets(student: StudentFact) -> tuple[set[str], set[str], set[str]]:
    passed = {code for code, outcome in student.attempts if outcome == "PASSED"}
    registered = {code for code, outcome in student.attempts if outcome == "IN_PROGRESS"}
    failed = {code for code, outcome in student.attempts if outcome == "FAILED"}
    return passed, registered, failed


def _eligibility(course: CourseFact, passed: set[str], registered: set[str]) -> str:
    if course.course_code in passed or course.course_code in registered:
        return "EXCLUDED"
    if course.prerequisite_status in {"unresolved", "source_conflict", "needs_review"}:
        return "REVIEW_REQUIRED"
    if not course.dependency_groups:
        return "ELIGIBLE"
    return "ELIGIBLE" if all(any(option in passed for option in group)
                             for group in course.dependency_groups) else "BLOCKED"


def _upcoming(course: CourseFact, plan_courses: dict[str, CourseFact], passed: set[str],
              registered: set[str]) -> bool:
    if _eligibility(course, passed, registered) == "ELIGIBLE":
        return True
    if course.prerequisite_status in {"unresolved", "source_conflict", "needs_review"}:
        return False
    for group in course.dependency_groups:
        if any(option in passed for option in group):
            continue
        if not any(option in plan_courses and _eligibility(plan_courses[option], passed, registered) == "ELIGIBLE"
                   for option in group):
            return False
    return bool(course.dependency_groups)


def _capacity_state(demand: int, capacity: int | None) -> str:
    if capacity is None:
        return "UNAVAILABLE"
    if demand > capacity:
        return "OVER_DEMAND"
    if capacity == 0:
        return "HEALTHY" if demand == 0 else "OVER_DEMAND"
    ratio = demand / capacity
    if ratio < 0.5:
        return "UNDER_CAPACITY"
    if ratio < 0.85:
        return "HEALTHY"
    return "NEAR_CAPACITY"


def _level(score: int) -> str:
    if score >= 75:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 25:
        return "WATCH"
    return "NONE"


def _score(*, required: bool, downstream: int, gap: int | None, projected: int,
           affected: int, total_students: int) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if required:
        score += 25
        reasons.append("REQUIRED_CORE_COURSE")
    if downstream:
        score += min(25, downstream * 5)
        reasons.append("VERIFIED_DOWNSTREAM_DEPENDENCIES")
    if gap is not None and gap > 0:
        score += min(30, round(30 * gap / max(projected, 1)))
        reasons.append("PROJECTED_DEMAND_EXCEEDS_CAPACITY")
    if affected:
        score += min(20, round(20 * affected / max(total_students, 1)))
        reasons.append("STUDENTS_AFFECTED")
    return min(100, score), reasons


def _filtered(snapshot: AnalyticsSnapshot, faculty: str | None, major: str | None,
              plan_key: str | None) -> tuple[list, list, list]:
    programs = [p for p in snapshot.programs
                if (not faculty or p.faculty_code == faculty)
                and (not major or p.major_code == major)
                and (not plan_key or p.plan_key == plan_key)]
    plan_ids = {p.plan_id for p in programs}
    courses = [c for c in snapshot.courses if c.plan_id in plan_ids]
    students = [s for s in snapshot.students if s.plan_id in plan_ids]
    if snapshot.assigned_student_ids is not None:
        students = [s for s in students if s.owner_id in snapshot.assigned_student_ids]
    return programs, courses, students


def build_dashboard(snapshot: AnalyticsSnapshot, *, faculty: str | None = None,
                    major: str | None = None, plan_key: str | None = None,
                    minimum_cohort_size: int = 3,
                    generated_at: datetime | None = None) -> DashboardResponse:
    """Build one internally consistent dashboard from a single immutable snapshot."""
    if minimum_cohort_size < 1:
        raise ValueError("minimum_cohort_size must be positive")
    programs, memberships, students = _filtered(snapshot, faculty, major, plan_key)
    programs_by_id = {p.plan_id: p for p in programs}
    courses_by_plan: dict[str, dict[str, CourseFact]] = defaultdict(dict)
    memberships_by_code: dict[str, list[CourseFact]] = defaultdict(list)
    for course in memberships:
        courses_by_plan[course.plan_id][course.course_code] = course
        memberships_by_code[course.course_code].append(course)
    students_by_plan: dict[str, list[StudentFact]] = defaultdict(list)
    for student in students:
        students_by_plan[student.plan_id].append(student)

    # Verified downstream edges are plan-specific. Unresolved relationships never become edges.
    downstream_by_plan: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for target in memberships:
        for group in target.dependency_groups:
            for prerequisite in group:
                downstream_by_plan[target.plan_id][prerequisite].add(target.course_code)

    def transitive(plan_id: str, code: str) -> set[str]:
        found: set[str] = set()
        stack = list(downstream_by_plan[plan_id].get(code, ()))
        while stack:
            item = stack.pop()
            if item in found:
                continue
            found.add(item)
            stack.extend(downstream_by_plan[plan_id].get(item, ()))
        return found

    section_by_code: dict[str, list] = defaultdict(list)
    if snapshot.sections is not None:
        for section in snapshot.sections:
            section_by_code[section.course_code].append(section)

    course_metrics: list[CourseMetric] = []
    student_opportunities: dict[str, set[str]] = defaultdict(set)
    student_blocked: dict[str, set[str]] = defaultdict(set)
    student_review: dict[str, set[str]] = defaultdict(set)
    student_pressure: dict[str, set[str]] = defaultdict(set)

    for code, course_memberships in memberships_by_code.items():
        eligible: set[str] = set()
        planned: set[str] = set()
        upcoming: set[str] = set()
        excluded: set[str] = set()
        registered_known: set[str] = set()
        demand_by_program: list[ProgramBreakdown] = []
        affected_programs: set[str] = set()
        downstream_codes: set[str] = set()
        prerequisite_review = any(c.prerequisite_status in {"unresolved", "source_conflict", "needs_review"}
                                  for c in course_memberships)
        for course in course_memberships:
            program = programs_by_id[course.plan_id]
            program_demand: set[str] = set()
            downstream_codes.update(transitive(course.plan_id, code))
            for student in students_by_plan[course.plan_id]:
                passed, registered, _ = _student_sets(student)
                state = _eligibility(course, passed, registered)
                if state == "EXCLUDED":
                    excluded.add(student.owner_id)
                    if code in registered:
                        registered_known.add(student.owner_id)
                    continue
                if state == "ELIGIBLE":
                    eligible.add(student.owner_id)
                    program_demand.add(student.owner_id)
                    student_opportunities[student.owner_id].add(code)
                elif state == "REVIEW_REQUIRED":
                    student_review[student.owner_id].add(code)
                else:
                    student_blocked[student.owner_id].add(code)
                if code in student.planned_courses:
                    planned.add(student.owner_id)
                    program_demand.add(student.owner_id)
                if _upcoming(course, courses_by_plan[course.plan_id], passed, registered):
                    upcoming.add(student.owner_id)
                    program_demand.add(student.owner_id)
            if program_demand:
                affected_programs.add(program.plan_key)
            demand_by_program.append(ProgramBreakdown(
                plan_key=program.plan_key, faculty_code=program.faculty_code,
                major_code=program.major_code,
                student_count=len(students_by_plan[course.plan_id]),
                demand_count=len(program_demand),
            ))
        projected_students = (eligible | planned | upcoming) - excluded
        projected = len(projected_students)
        sections = section_by_code.get(code, [])
        capacity = (sum(section.capacity for section in sections if section.capacity is not None)
                    if snapshot.sections is not None and all(s.capacity is not None for s in sections) else None)
        available = (sum(section.available for section in sections if section.available is not None)
                     if snapshot.sections is not None and all(s.available is not None for s in sections) else None)
        authoritative_registered = (sum(section.enrolled for section in sections if section.enrolled is not None)
                                    if snapshot.sections is not None and all(s.enrolled is not None for s in sections) else None)
        current_registered = authoritative_registered if authoritative_registered is not None else len(registered_known)
        gap = projected - capacity if capacity is not None else None
        required = any(c.requirement_type == "required" for c in course_memberships)
        score, reasons = _score(required=required, downstream=len(downstream_codes), gap=gap,
                                projected=projected, affected=len(projected_students),
                                total_students=len(students))
        state = _capacity_state(projected, capacity)
        if state in {"NEAR_CAPACITY", "OVER_DEMAND"}:
            for student_id in projected_students:
                student_pressure[student_id].add(code)
        utilization = (round(100 * current_registered / capacity, 1)
                       if capacity is not None and capacity > 0 else None)
        confidence = ("LOW" if prerequisite_review else "HIGH"
                      if snapshot.offering_complete and bool(students) else "MEDIUM"
                      if students else "INSUFFICIENT_DATA")
        recommendation = None
        helped = 0
        if gap is not None and gap > 0 and required and len(projected_students) >= minimum_cohort_size:
            recommendation = "CONSIDER_ADDITIONAL_SECTION"
            helped = gap
        course_metrics.append(CourseMetric(
            course_code=code,
            name_ar=next((c.name_ar for c in course_memberships if c.name_ar), None),
            name_en=next((c.name_en for c in course_memberships if c.name_en), None),
            programs=sorted({programs_by_id[c.plan_id].plan_key for c in course_memberships}),
            requirement_categories=sorted({c.requirement_group for c in course_memberships}),
            prerequisite_status="REVIEW_REQUIRED" if prerequisite_review else
                "VERIFIED" if any(c.dependency_groups for c in course_memberships) else "NOT_APPLICABLE",
            current_registered=_metric(current_registered, "students", inputs={
                "authoritative_offering_count": authoritative_registered,
                "synchronized_student_count": len(registered_known),
            }),
            eligible_not_registered=_metric(len(eligible), "students", reasons=["DETERMINISTIC_ELIGIBILITY"]),
            planned_need=_metric(len(planned), "students", reasons=["ACTIVE_VALID_PLAN_INTENT"]),
            degree_path_need=_metric(len(upcoming), "students", reasons=["ONE_VERIFIED_PREREQUISITE_HORIZON"]),
            projected_demand=_metric(projected, "students", inputs={
                "method": "DISTINCT_STUDENT_UNION", "currently_eligible": len(eligible),
                "planner_selected": len(planned), "degree_path_upcoming": len(upcoming),
            }),
            projection_confidence=confidence,
            projection_components=ProjectionComponents(
                currently_eligible=len(eligible), planner_selected=len(planned),
                degree_path_upcoming=len(upcoming), excluded_completed_or_registered=len(excluded)),
            offered_seats=_metric(capacity, "seats", status="AVAILABLE" if capacity is not None else "UNAVAILABLE",
                                  reasons=[] if capacity is not None else ["OFFERING_CAPACITY_UNAVAILABLE"]),
            available_seats=_metric(available, "seats", status="AVAILABLE" if available is not None else "UNAVAILABLE"),
            utilization_percent=_metric(utilization, "percent", status="AVAILABLE" if utilization is not None else "UNAVAILABLE"),
            demand_capacity_gap=_metric(gap, "students", status="AVAILABLE" if gap is not None else "UNAVAILABLE"),
            capacity_state=state,
            bottleneck_score=score, bottleneck_level=_level(score), bottleneck_reasons=reasons,
            affected_student_count=len(projected_students), downstream_course_count=len(downstream_codes),
            programs_affected=sorted(affected_programs), action_recommendation=recommendation,
            estimated_students_helped=helped, demand_by_program=sorted(demand_by_program, key=lambda x: x.plan_key),
        ))

    course_metrics.sort(key=lambda c: (-c.projected_demand.value, c.course_code))

    program_metrics: list[ProgramMetric] = []
    near_graduation: set[str] = set()
    blocked_paths: set[str] = set()
    for program in programs:
        cohort = students_by_plan[program.plan_id]
        progress_values: list[float] = []
        earned_values: list[float] = []
        registered_credits = 0.0
        band_counts = {key: 0 for key in ("0_24", "25_49", "50_74", "75_89", "90_100")}
        for student in cohort:
            passed, registered, _ = _student_sets(student)
            earned = student.earned_credits
            if earned is None:
                earned = sum(c.credits for code, c in courses_by_plan[program.plan_id].items() if code in passed)
            earned_values.append(float(earned))
            progress = min(100.0, round(100 * float(earned) / max(program.total_credits, 1), 1))
            progress_values.append(progress)
            band = "0_24" if progress < 25 else "25_49" if progress < 50 else "50_74" if progress < 75 else "75_89" if progress < 90 else "90_100"
            band_counts[band] += 1
            if progress >= 90:
                near_graduation.add(student.owner_id)
            registered_credits += sum(c.credits for code, c in courses_by_plan[program.plan_id].items() if code in registered)
            required_remaining = [c for c in courses_by_plan[program.plan_id].values()
                                  if c.requirement_type == "required" and c.course_code not in passed and c.course_code not in registered]
            if required_remaining and not any(_eligibility(c, passed, registered) == "ELIGIBLE" for c in required_remaining):
                blocked_paths.add(student.owner_id)
        small = 0 < len(cohort) < minimum_cohort_size
        status = "INSUFFICIENT_DATA" if not cohort else "SUPPRESSED" if small else "AVAILABLE"
        relevant = [c for c in course_metrics if program.plan_key in c.programs]
        program_metrics.append(ProgramMetric(
            plan_id=program.plan_id, plan_key=program.plan_key, plan_number=program.plan_number,
            faculty_code=program.faculty_code, faculty_name_ar=program.faculty_name_ar,
            major_code=program.major_code, major_name_ar=program.major_name_ar,
            student_count=len(cohort), data_status=status,
            average_progress_percent=None if small or not progress_values else round(sum(progress_values) / len(progress_values), 1),
            average_earned_credits=None if small or not earned_values else round(sum(earned_values) / len(earned_values), 1),
            median_earned_credits=None if small or not earned_values else round(float(median(earned_values)), 1),
            current_registered_credits=round(registered_credits, 1),
            blocked_student_count=None if small else len({s.owner_id for s in cohort if s.owner_id in blocked_paths}),
            review_required_count=None if small else len({s.owner_id for s in cohort if student_review[s.owner_id]}),
            progress_distribution=[ProgressBand(
                band=band, student_count=None if small else count,
                status="SUPPRESSED" if small else "AVAILABLE" if cohort else "INSUFFICIENT_DATA",
            ) for band, count in band_counts.items()],
            high_demand_courses=[c.course_code for c in sorted(relevant, key=lambda x: (-x.projected_demand.value, x.course_code))[:5]
                                 if c.projected_demand.value],
            bottleneck_courses=[c.course_code for c in sorted(relevant, key=lambda x: (-x.bottleneck_score, x.course_code))[:5]
                                if c.bottleneck_level in {"HIGH", "CRITICAL"}],
        ))
    program_metrics.sort(key=lambda p: p.plan_key)

    review_items: list[ReviewQueueItem] = []
    for code, items in memberships_by_code.items():
        unresolved = sorted({dep for item in items for dep in item.unresolved_dependency_codes})
        if not unresolved and not any(i.prerequisite_status in {"unresolved", "source_conflict", "needs_review"} for i in items):
            continue
        plans = sorted({programs_by_id[i.plan_id].plan_key for i in items})
        affected = {s.owner_id for item in items for s in students_by_plan[item.plan_id]
                    if _eligibility(item, *_student_sets(s)[:2]) == "REVIEW_REQUIRED"}
        review_items.append(ReviewQueueItem(
            course_code=code, unresolved_prerequisite_codes=unresolved,
            affected_plans=plans, affected_student_count=len(affected),
            downstream_course_count=len({d for i in items for d in transitive(i.plan_id, code)}),
        ))

    faculty_counts: dict[str, int] = defaultdict(int)
    major_counts: dict[str, int] = defaultdict(int)
    for student in students:
        program = programs_by_id[student.plan_id]
        faculty_counts[program.faculty_code] += 1
        major_counts[program.major_code] += 1
    known_registered_credits = sum(p.current_registered_credits for p in program_metrics)
    synchronized_current_regs = sum(1 for s in students for _, outcome in s.attempts if outcome == "IN_PROGRESS")
    authoritative_current_regs = (sum(section.enrolled for section in snapshot.sections
                                      if section.enrolled is not None)
                                  if snapshot.sections is not None
                                  and all(section.enrolled is not None for section in snapshot.sections) else None)
    current_regs = authoritative_current_regs if authoritative_current_regs is not None else synchronized_current_regs
    avg_load = round(known_registered_credits / len(students), 1) if students else None
    pressure = [c for c in course_metrics if c.capacity_state in {"NEAR_CAPACITY", "OVER_DEMAND"}]
    bottlenecks = [c for c in course_metrics if c.bottleneck_level in {"HIGH", "CRITICAL"}]
    role_scope = "ADVISOR_ASSIGNED" if snapshot.assigned_student_ids is not None else "INSTITUTION_ADMIN"
    return DashboardResponse(
        university_id=snapshot.university_id, term_key=snapshot.term_key, role_scope=role_scope,
        filters={"faculty": faculty, "major": major, "plan_key": plan_key},
        minimum_cohort_size=minimum_cohort_size,
        overview=Overview(
            total_active_students=_metric(len(students), "students"),
            current_registrations=_metric(current_regs, "registrations", inputs={
                "source": "AUTHORITATIVE_OFFERING_ENROLLMENT" if authoritative_current_regs is not None
                          else "SYNCHRONIZED_IN_PROGRESS_ATTEMPTS",
                "synchronized_in_progress": synchronized_current_regs,
            }),
            average_registered_credit_load=_metric(avg_load, "credits", status="AVAILABLE" if avg_load is not None else "INSUFFICIENT_DATA"),
            eligible_course_opportunities=_metric(sum(len(v) for v in student_opportunities.values()), "student_course_opportunities"),
            blocked_by_prerequisite=_metric(sum(len(v) for v in student_blocked.values()), "student_course_blocks"),
            review_required=_metric(sum(len(v) for v in student_review.values()), "student_course_reviews"),
            high_demand_courses=_metric(sum(1 for c in course_metrics if (c.projected_demand.value or 0) >= minimum_cohort_size), "courses"),
            capacity_pressure_courses=_metric(len(pressure), "courses"),
            academic_bottlenecks=_metric(len(bottlenecks), "courses"),
            approaching_graduation=_metric(len(near_graduation), "students", reasons=["PROGRESS_AT_LEAST_90_PERCENT"]),
            blocked_degree_paths=_metric(len(blocked_paths), "students", reasons=["NO_ELIGIBLE_REQUIRED_COURSE"]),
            students_by_faculty=dict(sorted(faculty_counts.items())),
            students_by_major=dict(sorted(major_counts.items())),
        ),
        programs=program_metrics, courses=course_metrics, review_queue=review_items,
        advisor_caseload=AdvisorCaseload(
            scope="ASSIGNED_STUDENTS" if snapshot.assigned_student_ids is not None else "INSTITUTION",
            assigned_student_count=len(students) if snapshot.assigned_student_ids is not None else None,
            prerequisite_review=len(student_review), blocked_degree_paths=len(blocked_paths),
            near_graduation=len(near_graduation),
            registration_conflicts=_metric(None, "students", status="UNAVAILABLE", reasons=["CONFLICT_AGGREGATE_NOT_SYNCHRONIZED"]),
            approaching_credit_limit=_metric(None, "students", status="UNAVAILABLE", reasons=["INSTITUTIONAL_CREDIT_LIMIT_NOT_CONFIGURED"]),
            without_viable_semester_plan=len(blocked_paths), impacted_by_high_pressure_courses=len(student_pressure),
            reason_codes=["DETERMINISTIC_ACADEMIC_STATE", "NO_ARBITRARY_RISK_LABEL"],
        ),
        methodology={"projected_demand": PROJECTION_METHOD, "bottleneck_score": BOTTLENECK_METHOD,
                     "capacity_state": CAPACITY_METHOD, "privacy": "Small-cohort progress distributions are suppressed."},
        source_versions={"catalog": snapshot.catalog_version, "student_state": snapshot.student_state_version,
                         "offerings": snapshot.offering_version or "UNAVAILABLE"},
        generated_at=generated_at or datetime.now(timezone.utc),
    )


def simulate_capacity(course: CourseMetric, request: SimulationRequest) -> SimulationResponse:
    """Apply bounded arithmetic to a response DTO only; authoritative state is never written."""
    before = int(course.offered_seats.value) if course.offered_seats.value is not None else None
    projected = int(course.projected_demand.value or 0)
    assumptions: list[str] = ["SIMULATION_ONLY", "AUTHORITATIVE_DATA_NOT_MUTATED"]
    if request.kind == "REMOVE_OFFERING":
        after = 0
        assumptions.append("ALL_SELECTED_COURSE_CAPACITY_REMOVED")
    elif request.kind == "ADD_SECTION":
        if request.seats is None or request.seats <= 0:
            raise ValueError("ADD_SECTION requires positive seats")
        after = None if before is None else before + request.seats
        assumptions.append(f"ONE_ADDITIONAL_SECTION_WITH_{request.seats}_SEATS")
    else:
        if request.seats is None or request.section_id is None:
            raise ValueError("CHANGE_SECTION_CAPACITY requires section_id and seats")
        # Course response intentionally exposes no section-level capacity. The bounded scenario
        # treats `seats` as the requested course-level replacement and labels that assumption.
        after = request.seats
        assumptions.append("REQUESTED_CAPACITY_TREATED_AS_COURSE_TOTAL")
    gap_before = projected - before if before is not None else None
    gap_after = projected - after if after is not None else None
    helped = 0
    if gap_before is not None and gap_after is not None:
        helped = max(0, min(max(gap_before, 0), max(0, before - after) if after < before else after - before))
    score_after, _ = _score(
        required="REQUIRED_CORE_COURSE" in course.bottleneck_reasons,
        downstream=course.downstream_course_count, gap=gap_after, projected=projected,
        affected=projected, total_students=max(projected, 1),
    )
    return SimulationResponse(
        course_code=course.course_code, kind=request.kind,
        capacity_before=before, capacity_after=after,
        demand_gap_before=gap_before, demand_gap_after=gap_after,
        estimated_students_helped=helped,
        bottleneck_score_before=course.bottleneck_score, bottleneck_score_after=score_after,
        affected_programs=course.programs_affected,
        affected_eligible_students=int(course.eligible_not_registered.value or 0),
        affected_degree_paths=int(course.degree_path_need.value or 0),
        downstream_courses_impacted=course.downstream_course_count,
        assumptions=assumptions,
    )
