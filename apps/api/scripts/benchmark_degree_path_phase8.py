"""Local-only Phase 8 Degree Path benchmark; performs no database writes."""

from __future__ import annotations

import asyncio
import ctypes
import gc
import json
import os
from pathlib import Path
from decimal import Decimal
import sys
from threading import Event, Thread
from time import perf_counter
from time import sleep

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.catalog.supabase_repository import SupabaseAcademicCatalogRepository
from app.degree_path.engine import plan_degree_paths
from app.degree_path.models import DegreePathConstraints, canonical_semantic_fingerprint
from app.progress.models import (
    AcademicProgressCatalog, ProgressPlanCourse, ProgressRequirementGroup,
    ProgressStudyPlan, RequirementType,
)
from app.rules.models import (
    CanTakeCatalog, CourseCatalogStatus, CourseIdentity, PlanCourseRule,
    PrerequisiteLogicStatus,
)

LOCAL_URL = os.getenv("MORSHIDI_LOCAL_SUPABASE_URL", "http://127.0.0.1:54321")
LOCAL_KEY = os.getenv(
    "MORSHIDI_LOCAL_SUPABASE_SERVER_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
)
PLAN_CASES = {
    "ai_plan_12": "10000000-0000-0000-0000-000000000005",
    "nursing_plan_12": "2a78bbbb-0dc0-5c46-8630-7a46e4179830",
}


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def _working_set_bytes() -> int:
    if os.name != "nt":
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    psapi = ctypes.windll.psapi  # type: ignore[attr-defined]
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = (
        ctypes.c_void_p, ctypes.POINTER(_ProcessMemoryCounters), ctypes.c_ulong,
    )
    process = kernel32.GetCurrentProcess()
    if not psapi.GetProcessMemoryInfo(
        process, ctypes.byref(counters), counters.cb,
    ):
        raise OSError("GetProcessMemoryInfo failed")
    return int(counters.WorkingSetSize)


class _MemorySampler:
    def __init__(self) -> None:
        self._stop = Event()
        self.peak = 0
        self._thread = Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.is_set():
            self.peak = max(self.peak, _working_set_bytes())
            sleep(0.01)

    def __enter__(self):
        self.peak = _working_set_bytes()
        self._thread.start()
        return self

    def __exit__(self, *_args) -> None:
        self._stop.set()
        self._thread.join(timeout=1)
        self.peak = max(self.peak, _working_set_bytes())


def _large_synthetic_catalog(course_count: int = 60) -> tuple[AcademicProgressCatalog, CanTakeCatalog]:
    plan_id = "phase8-large-synthetic-plan"
    group_id = "phase8-large-synthetic-required"
    total = Decimal(course_count * 3)
    group = ProgressRequirementGroup(
        group_id=group_id, study_plan_id=plan_id, group_code="SYNTHETIC_REQUIRED",
        name_ar="متطلبات تجريبية كبيرة", name_en="Large synthetic requirements",
        scope="major", requirement_type=RequirementType.REQUIRED,
        required_credit_hours=total, display_order=1,
    )
    codes = tuple(f"SYN{index:03d}" for index in range(1, course_count + 1))
    progress = AcademicProgressCatalog(
        study_plan=ProgressStudyPlan(plan_id, total),
        requirement_groups=(group,),
        plan_courses=tuple(ProgressPlanCourse(
            plan_course_id=f"pc-{code}", study_plan_id=plan_id,
            requirement_group_id=group_id, course_code=code,
            catalog_status=CourseCatalogStatus.KNOWN, credit_hours=Decimal("3"),
            display_order=index,
        ) for index, code in enumerate(codes, 1)),
    )
    eligibility = CanTakeCatalog(
        study_plan_id=plan_id,
        plan_courses=tuple(PlanCourseRule(
            course_code=code, prerequisite_logic_status=PrerequisiteLogicStatus.NOT_APPLICABLE,
            dependency_groups=(), raw_prerequisite_text=None,
        ) for code in codes),
        courses=tuple(CourseIdentity(code, CourseCatalogStatus.KNOWN) for code in codes),
    )
    return progress, eligibility


def _calculate(progress: AcademicProgressCatalog, eligibility: CanTakeCatalog) -> tuple[dict, tuple[str, ...]]:
    metrics: dict[str, float | int] = {}
    started = perf_counter()
    result = plan_degree_paths(
        progress, eligibility, (),
        DegreePathConstraints(
            max_credit_hours_per_semester=Decimal("15"), max_courses_per_semester=5,
            max_semesters_ahead=16, max_paths=3, multi_strategy=True,
        ),
        metrics=metrics,
    )
    engine_ms = (perf_counter() - started) * 1000
    fingerprints = tuple(repr(canonical_semantic_fingerprint(path)) for path in result.paths)
    return {
        "engine_ms": round(engine_ms, 3),
        "validation_ms": round(float(metrics.get("validation_ms", 0)), 3),
        "semester_planner_ms": round(float(metrics.get("semester_planner_ms", 0)), 3),
        "path_count": len(result.paths),
        "statuses": [path.status.value for path in result.paths],
    }, fingerprints


async def _benchmark_db_case(repository: SupabaseAcademicCatalogRepository, plan_id: str) -> list[dict]:
    runs = []
    for _ in range(2):
        gc.collect()
        with _MemorySampler() as memory:
            total_started = perf_counter()
            context_started = perf_counter()
            progress, eligibility = await asyncio.gather(
                repository.load_progress_catalog(plan_id),
                repository.load_plan_eligibility_catalog(plan_id),
            )
            context_ms = (perf_counter() - context_started) * 1000
            calculation, fingerprints = _calculate(progress, eligibility)
            total_ms = (perf_counter() - total_started) * 1000
        runs.append({
            "end_to_end_ms": round(total_ms, 3), "academic_context_ms": round(context_ms, 3),
            "peak_process_working_set_mib": round(memory.peak / 1024 / 1024, 3), **calculation,
            "fingerprints": fingerprints,
        })
    return runs


def _benchmark_large_synthetic() -> list[dict]:
    runs = []
    for _ in range(2):
        gc.collect()
        with _MemorySampler() as memory:
            total_started = perf_counter()
            context_started = perf_counter()
            progress, eligibility = _large_synthetic_catalog()
            context_ms = (perf_counter() - context_started) * 1000
            calculation, fingerprints = _calculate(progress, eligibility)
            total_ms = (perf_counter() - total_started) * 1000
        runs.append({
            "end_to_end_ms": round(total_ms, 3), "academic_context_ms": round(context_ms, 3),
            "peak_process_working_set_mib": round(memory.peak / 1024 / 1024, 3), **calculation,
            "fingerprints": fingerprints,
        })
    return runs


async def main() -> None:
    if LOCAL_URL not in {"http://127.0.0.1:54321", "http://localhost:54321"}:
        raise SystemExit("Refusing non-local Supabase URL")
    if LOCAL_KEY.endswith(".invalid"):
        raise SystemExit("Set MORSHIDI_LOCAL_SUPABASE_SERVER_KEY from `supabase status --output env`")
    async with httpx.AsyncClient(timeout=30) as client:
        repository = SupabaseAcademicCatalogRepository(LOCAL_URL, LOCAL_KEY, client=client)
        report = {name: await _benchmark_db_case(repository, plan_id)
                  for name, plan_id in PLAN_CASES.items()}
    report["large_synthetic_180_credits_60_courses"] = _benchmark_large_synthetic()
    for name, runs in report.items():
        if runs[0]["fingerprints"] != runs[1]["fingerprints"]:
            raise RuntimeError(f"{name} changed semantic result on repeat")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
