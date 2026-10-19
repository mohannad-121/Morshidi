"""Synchronization orchestrator for full and incremental SIS state ingestion."""

from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any, Protocol
from uuid import UUID

from .adapter_interface import SISAdapter
from .capabilities import SISCapability
from .errors import CapabilityNotSupportedError, SISIntegrationError
from .mapping_layer import MappingLayer
from .models import (
    ChangeBatch,
    NormalizedCourse,
    NormalizedEnrollment,
    NormalizedGradeAttempt,
    NormalizedOffering,
    NormalizedStudent,
    SyncJob,
)


class SyncPersistenceCallback(Protocol):
    """Callback protocol for persisting normalized SIS entities into Morshidi database."""

    async def upsert_student_record(self, university_id: UUID, student: NormalizedStudent) -> bool:
        ...

    async def upsert_grade_record(self, university_id: UUID, student_id: str, grade: NormalizedGradeAttempt) -> bool:
        ...

    async def upsert_enrollment_record(self, university_id: UUID, student_id: str, enrollment: NormalizedEnrollment) -> bool:
        ...

    async def upsert_offering_record(self, university_id: UUID, offering: NormalizedOffering) -> bool:
        ...


class SyncOrchestrator:
    """Orchestrates bidirectional/inbound sync jobs between external SIS and Morshidi shadow state."""

    def __init__(
        self,
        university_id: UUID,
        adapter: SISAdapter,
        mapping_layer: MappingLayer | None = None,
        persistence_callback: SyncPersistenceCallback | None = None,
    ) -> None:
        self.university_id = university_id
        self.adapter = adapter
        self.mapping = mapping_layer or MappingLayer(university_id)
        self.persistence = persistence_callback

    async def run_full_sync(self, *, terms_to_sync: list[str] | None = None) -> SyncJob:
        """Execute a full sync of terms, offerings, and catalog."""
        start_time = perf_counter()
        job = SyncJob(
            university_id=self.university_id,
            sync_mode="FULL_SYNC",
            status="RUNNING",
            started_at=datetime.utcnow(),
        )

        try:
            # 1. Sync academic terms
            terms = await self.adapter.get_terms()
            job.records_processed += len(terms)
            target_terms = terms_to_sync or [t.term_code for t in terms if t.is_current or t.is_registration_open]
            if not target_terms and terms:
                target_terms = [terms[0].term_code]

            # 2. Sync offerings for target terms if capability supported
            if SISCapability.OFFERINGS_READ in self.adapter.capabilities:
                for term_code in target_terms:
                    offerings = await self.adapter.get_course_offerings(term_code)
                    job.records_processed += len(offerings)
                    for off in offerings:
                        try:
                            if self.persistence:
                                created = await self.persistence.upsert_offering_record(self.university_id, off)
                                if created:
                                    job.records_created += 1
                                else:
                                    job.records_updated += 1
                            else:
                                job.records_skipped += 1
                        except Exception as item_err:
                            job.records_failed += 1
                            job.errors.append(f"Offering {off.section_id} failed: {item_err}")

            # 3. Get latest cursor
            job.cursor_after = await self.adapter.get_cursor_or_change_token()
            job.status = "SUCCEEDED" if job.records_failed == 0 else "PARTIAL"

        except Exception as err:
            job.status = "FAILED"
            job.errors.append(str(err))

        finally:
            job.duration_ms = int((perf_counter() - start_time) * 1000)
            job.completed_at = datetime.utcnow()

        return job

    async def run_incremental_sync(self, cursor: str | None) -> SyncJob:
        """Execute an incremental sync utilizing SIS change tracking."""
        if SISCapability.INCREMENTAL_SYNC not in self.adapter.capabilities:
            raise CapabilityNotSupportedError(
                f"Adapter '{self.adapter.provider_type}' does not support INCREMENTAL_SYNC"
            )

        start_time = perf_counter()
        job = SyncJob(
            university_id=self.university_id,
            sync_mode="INCREMENTAL_SYNC",
            status="RUNNING",
            cursor_before=cursor,
            started_at=datetime.utcnow(),
        )

        try:
            batch: ChangeBatch = await self.adapter.fetch_changes_since(cursor)
            job.cursor_after = batch.cursor or cursor

            # Process students
            for student in batch.students:
                job.records_processed += 1
                try:
                    if self.persistence:
                        created = await self.persistence.upsert_student_record(self.university_id, student)
                        if created:
                            job.records_created += 1
                        else:
                            job.records_updated += 1
                    else:
                        job.records_skipped += 1
                except Exception as err:
                    job.records_failed += 1
                    job.errors.append(f"Student {student.university_student_id} failed: {err}")

            # Process grades
            for grade in batch.grades:
                job.records_processed += 1
                try:
                    if self.persistence:
                        # Attempt to resolve canonical course code
                        mapped = self.mapping.resolve_external("COURSE", grade.course_code, required=False)
                        target_code = mapped.canonical_code if mapped else grade.course_code
                        normalized_grade = grade.model_copy(update={"course_code": target_code})
                        # Persistence needs student id if present in raw payload or external
                        student_id = grade.raw_payload.get("student_id") or "UNKNOWN"
                        created = await self.persistence.upsert_grade_record(self.university_id, student_id, normalized_grade)
                        if created:
                            job.records_created += 1
                        else:
                            job.records_updated += 1
                    else:
                        job.records_skipped += 1
                except Exception as err:
                    job.records_failed += 1
                    job.errors.append(f"Grade {grade.course_code} failed: {err}")

            # Process enrollments
            for enrollment in batch.enrollments:
                job.records_processed += 1
                try:
                    if self.persistence:
                        mapped = self.mapping.resolve_external("COURSE", enrollment.course_code, required=False)
                        target_code = mapped.canonical_code if mapped else enrollment.course_code
                        normalized_enr = enrollment.model_copy(update={"course_code": target_code})
                        student_id = enrollment.raw_payload.get("student_id") or "UNKNOWN"
                        created = await self.persistence.upsert_enrollment_record(self.university_id, student_id, normalized_enr)
                        if created:
                            job.records_created += 1
                        else:
                            job.records_updated += 1
                    else:
                        job.records_skipped += 1
                except Exception as err:
                    job.records_failed += 1
                    job.errors.append(f"Enrollment {enrollment.course_code}:{enrollment.section_code} failed: {err}")

            job.status = "SUCCEEDED" if job.records_failed == 0 else "PARTIAL"

        except Exception as err:
            job.status = "FAILED"
            job.errors.append(str(err))

        finally:
            job.duration_ms = int((perf_counter() - start_time) * 1000)
            job.completed_at = datetime.utcnow()

        return job

