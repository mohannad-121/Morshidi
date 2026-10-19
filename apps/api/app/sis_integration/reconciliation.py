"""Reconciliation and conflict detection engine between authoritative SIS and Morshidi shadow state."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from .models import (
    NormalizedEnrollment,
    NormalizedGradeAttempt,
    NormalizedStudent,
    ReconciliationItem,
)


class ReconciliationEngine:
    """Detects discrepancies between external authoritative SIS state and Morshidi shadow state.

    Guiding principle:
    - THE UNIVERSITY SIS REMAINS AUTHORITATIVE for official enrollment and grades.
    - Morshidi intelligence (diagnostics, advice, simulations) is NEVER overwritten.
    - Reconciliation detects drift and produces actionable items without silent state corruption.
    """

    @staticmethod
    def reconcile_student_profile(
        university_id: UUID,
        authoritative: NormalizedStudent,
        local_shadow: dict[str, Any] | None,
    ) -> list[ReconciliationItem]:
        items: list[ReconciliationItem] = []
        ext_id = authoritative.university_student_id

        if not local_shadow:
            items.append(ReconciliationItem(
                university_id=university_id,
                entity_type="STUDENT",
                external_identifier=ext_id,
                status="MISSING_LOCALLY",
                details={
                    "message": f"Student '{ext_id}' exists in SIS but has no local shadow profile",
                    "authoritative": authoritative.model_dump(mode="json"),
                },
            ))
            return items

        # Check GPA drift
        local_gpa = local_shadow.get("cumulative_gpa")
        if authoritative.cumulative_gpa is not None and local_gpa is not None:
            if Decimal(str(authoritative.cumulative_gpa)) != Decimal(str(local_gpa)):
                items.append(ReconciliationItem(
                    university_id=university_id,
                    entity_type="STUDENT",
                    external_identifier=ext_id,
                    status="STALE_LOCALLY",
                    details={
                        "field": "cumulative_gpa",
                        "authoritative_gpa": str(authoritative.cumulative_gpa),
                        "local_gpa": str(local_gpa),
                    },
                ))

        # Check earned credits drift
        local_credits = local_shadow.get("earned_credit_hours")
        if authoritative.earned_credit_hours is not None and local_credits is not None:
            if Decimal(str(authoritative.earned_credit_hours)) != Decimal(str(local_credits)):
                items.append(ReconciliationItem(
                    university_id=university_id,
                    entity_type="STUDENT",
                    external_identifier=ext_id,
                    status="STALE_LOCALLY",
                    details={
                        "field": "earned_credit_hours",
                        "authoritative_credits": str(authoritative.earned_credit_hours),
                        "local_credits": str(local_credits),
                    },
                ))

        # Check academic standing drift
        local_standing = local_shadow.get("academic_standing")
        if authoritative.academic_standing and local_standing:
            if authoritative.academic_standing.strip().upper() != str(local_standing).strip().upper():
                items.append(ReconciliationItem(
                    university_id=university_id,
                    entity_type="STUDENT",
                    external_identifier=ext_id,
                    status="VALUE_MISMATCH",
                    details={
                        "field": "academic_standing",
                        "authoritative": authoritative.academic_standing,
                        "local": str(local_standing),
                    },
                ))

        if not items:
            items.append(ReconciliationItem(
                university_id=university_id,
                entity_type="STUDENT",
                external_identifier=ext_id,
                status="IN_SYNC",
                details={"student_id": ext_id},
            ))

        return items

    @staticmethod
    def reconcile_enrollments(
        university_id: UUID,
        student_id: str,
        authoritative_enrollments: list[NormalizedEnrollment],
        local_enrollments: list[dict[str, Any]],
    ) -> list[ReconciliationItem]:
        items: list[ReconciliationItem] = []
        # Key: (course_code, section_code)
        local_map = {
            (str(e.get("course_code") or "").upper(), str(e.get("section_code") or e.get("section_id") or "").upper()): e
            for e in local_enrollments
        }
        auth_map = {
            (e.course_code.upper(), e.section_code.upper()): e
            for e in authoritative_enrollments
            if e.status == "ENROLLED"
        }

        # Check missing or status mismatches in local
        for key, auth_enr in auth_map.items():
            loc_enr = local_map.get(key)
            if not loc_enr:
                items.append(ReconciliationItem(
                    university_id=university_id,
                    entity_type="ENROLLMENT",
                    external_identifier=f"{student_id}:{auth_enr.course_code}:{auth_enr.section_code}",
                    status="MISSING_LOCALLY",
                    details={
                        "student_id": student_id,
                        "course_code": auth_enr.course_code,
                        "section_code": auth_enr.section_code,
                    },
                ))

        # Check orphaned local enrollments not in SIS
        for key, loc_enr in local_map.items():
            if key not in auth_map:
                items.append(ReconciliationItem(
                    university_id=university_id,
                    entity_type="ENROLLMENT",
                    external_identifier=f"{student_id}:{key[0]}:{key[1]}",
                    status="VALUE_MISMATCH",
                    details={
                        "student_id": student_id,
                        "message": "Enrollment exists locally but is absent from authoritative SIS",
                        "course_code": key[0],
                        "section_code": key[1],
                    },
                ))

        if not items:
            items.append(ReconciliationItem(
                university_id=university_id,
                entity_type="ENROLLMENT",
                external_identifier=student_id,
                status="IN_SYNC",
                details={"enrolled_count": len(auth_map)},
            ))

        return items

    @staticmethod
    def reconcile_grades(
        university_id: UUID,
        student_id: str,
        authoritative_grades: list[NormalizedGradeAttempt],
        local_grades: list[dict[str, Any]],
    ) -> list[ReconciliationItem]:
        items: list[ReconciliationItem] = []
        # Key: (course_code, term_code, attempt_sequence)
        local_map = {
            (
                str(g.get("course_code") or "").upper(),
                str(g.get("term_code") or "").upper(),
                int(g.get("attempt_sequence") or 1),
            ): g
            for g in local_grades
        }

        for auth_g in authoritative_grades:
            key = (auth_g.course_code.upper(), auth_g.term_code.upper(), auth_g.attempt_sequence)
            loc_g = local_map.get(key)
            if not loc_g:
                items.append(ReconciliationItem(
                    university_id=university_id,
                    entity_type="GRADE",
                    external_identifier=f"{student_id}:{auth_g.course_code}:{auth_g.term_code}",
                    status="MISSING_LOCALLY",
                    details={
                        "student_id": student_id,
                        "course_code": auth_g.course_code,
                        "outcome": auth_g.outcome,
                    },
                ))
            else:
                loc_outcome = str(loc_g.get("outcome") or "").upper()
                if auth_g.outcome != loc_outcome:
                    items.append(ReconciliationItem(
                        university_id=university_id,
                        entity_type="GRADE",
                        external_identifier=f"{student_id}:{auth_g.course_code}:{auth_g.term_code}",
                        status="VALUE_MISMATCH",
                        details={
                            "student_id": student_id,
                            "course_code": auth_g.course_code,
                            "authoritative_outcome": auth_g.outcome,
                            "local_outcome": loc_outcome,
                        },
                    ))

        if not items:
            items.append(ReconciliationItem(
                university_id=university_id,
                entity_type="GRADE",
                external_identifier=student_id,
                status="IN_SYNC",
                details={"grades_count": len(authoritative_grades)},
            ))

        return items

