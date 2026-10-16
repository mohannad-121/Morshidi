"""Owner-scoped state machine for the quick diagnostic."""

from __future__ import annotations

from datetime import datetime

from app.services.student import StudentService
from app.student_intelligence import diagnostic_v1
from app.student_intelligence.diagnostic import (
    ASSESSMENT_VERSION, MAX_RESPONSE_TIME_MS, QUESTIONS_BY_ID, SCORING_POLICY_VERSION,
    TARGET_QUESTIONS, AnswerEvidence, DiagnosticDomain, DiagnosticDomainResult,
    public_question, score_domain, select_next_question,
)
from app.student_intelligence.diagnostic_repository import (DiagnosticRepositoryError,
                                                            SupabaseDiagnosticRepository)


class DiagnosticNotFound(RuntimeError):
    pass


class DiagnosticConflict(RuntimeError):
    pass


class DiagnosticService:
    def __init__(self, repository: SupabaseDiagnosticRepository, students: StudentService) -> None:
        self._repository = repository
        self._students = students

    async def status(self, owner: str,
                     requested_version: str = diagnostic_v1.ASSESSMENT_VERSION) -> dict[str, object]:
        state = await self._students.get_profile(owner)
        active = await self._repository.load_active(
            owner, state.study_plan_id, diagnostic_v1.ASSESSMENT_VERSION)
        if active is None:
            active = await self._repository.load_active(owner, state.study_plan_id, requested_version)
        completed, _ = await self._repository.latest_completed(
            owner, state.study_plan_id, requested_version)
        return {"onboarding_status": "IN_PROGRESS" if active else "COMPLETED" if completed else "NOT_STARTED",
                "diagnostic_completed": completed is not None,
                "active_session_id": active["id"] if active else None,
                "latest_assessment_version": completed["assessment_version"] if completed else None,
                "latest_completed_at": completed["completed_at"] if completed else None}

    async def start(self, owner: str,
                    requested_version: str = diagnostic_v1.ASSESSMENT_VERSION) -> dict[str, object]:
        state = await self._students.get_profile(owner)
        active = await self._repository.load_active(
            owner, state.study_plan_id, diagnostic_v1.ASSESSMENT_VERSION)
        if active is None:
            active = await self._repository.load_active(owner, state.study_plan_id, requested_version)
        if active is None:
            institution = await self._students.resolve_student_university_id(owner)
            first = (select_next_question(()) if requested_version == ASSESSMENT_VERSION
                     else diagnostic_v1.select_next_question(()))
            assert first is not None
            try:
                active = await self._repository.create_session(
                    owner, state.profile_id, institution, state.study_plan_id,
                    requested_version, first.question_id)
            except DiagnosticRepositoryError:
                # A concurrent start may have won the partial-unique-index race.
                # Resume only the same owner's now-active session; otherwise fail closed.
                active = await self._repository.load_active(
                    owner, state.study_plan_id, requested_version)
                if active is None:
                    raise DiagnosticConflict("Diagnostic session was not started")
        return self._session_payload(active)

    async def next_question(self, owner: str, session_id: str) -> dict[str, object]:
        session = await self._owned_session(owner, session_id)
        return self._session_payload(session)

    async def answer(self, owner: str, session_id: str, question_id: str,
                     selected_option: str, response_time_ms: int | None,
                     self_confidence: str | None) -> dict[str, object]:
        session = await self._owned_session(owner, session_id)
        if session["status"] != "IN_PROGRESS" or session["current_question_id"] != question_id:
            raise DiagnosticConflict("Question is not currently issued")
        if session["assessment_version"] == diagnostic_v1.ASSESSMENT_VERSION:
            return await self._answer_v1(owner, session_id, question_id, selected_option, session)
        if session["assessment_version"] != ASSESSMENT_VERSION:
            raise DiagnosticConflict("Unsupported diagnostic assessment version")
        if response_time_ms is None or self_confidence is None:
            raise DiagnosticConflict("V2 diagnostic evidence is required")
        question = QUESTIONS_BY_ID.get(question_id)
        if question is None or selected_option not in {option.option_id for option in question.options}:
            raise DiagnosticConflict("Invalid diagnostic answer")
        if not 0 <= response_time_ms <= MAX_RESPONSE_TIME_MS or self_confidence not in {
            "LOW", "MEDIUM", "HIGH"
        }:
            raise DiagnosticConflict("Invalid diagnostic evidence")
        prior = tuple(AnswerEvidence(row["question_id"], row["selected_option"], row["is_correct"],
                                     int(row["response_time_ms"]), row["self_confidence"])
                      for row in await self._repository.load_responses(session_id))
        answered = AnswerEvidence(question_id, selected_option,
                                  selected_option == question.correct_option,
                                  response_time_ms, self_confidence)
        all_answers = prior + (answered,)
        next_item = select_next_question(all_answers)
        results = None
        if next_item is None:
            scored = [score_domain(domain, all_answers) for domain in DiagnosticDomain]
            results = [{"domain": row.domain.value, "score": row.score, "confidence": row.confidence,
                        "response_count": row.response_count, "reason_codes": list(row.reason_codes),
                        "reasoning_patterns": list(row.reasoning_patterns),
                        "scoring_policy_version": SCORING_POLICY_VERSION} for row in scored]
        try:
            updated = await self._repository.record_answer_v2(
                session_id=session_id, owner=owner, question_id=question_id,
                selected_option=selected_option, domain=question.domain.value,
                difficulty=question.difficulty, is_correct=answered.is_correct,
                response_time_ms=response_time_ms, self_confidence=self_confidence,
                next_question_id=next_item.question_id if next_item else None, results=results)
        except DiagnosticRepositoryError as exc:
            # Includes duplicate/concurrent answers and a session closed after
            # the pre-read. Never reveal database or answer-key detail.
            raise DiagnosticConflict("Diagnostic answer was not accepted") from exc
        payload = self._session_payload(updated)
        if results is not None:
            payload["results"] = [{key: row[key] for key in (
                "domain", "score", "confidence", "response_count", "reasoning_patterns"
            )} for row in results]
            payload["intelligence_profile"] = await self._students.get_student_intelligence_v2(owner)
        return payload

    async def _answer_v1(self, owner: str, session_id: str, question_id: str,
                         selected_option: str, session: dict[str, object]) -> dict[str, object]:
        question = diagnostic_v1.QUESTIONS_BY_ID.get(question_id)
        if question is None or selected_option not in {
            option.option_id for option in question.options
        }:
            raise DiagnosticConflict("Invalid diagnostic answer")
        prior = tuple(
            diagnostic_v1.AnswerEvidence(
                row["question_id"], row["selected_option"], row["is_correct"]
            )
            for row in await self._repository.load_responses(session_id)
        )
        answered = diagnostic_v1.AnswerEvidence(
            question_id, selected_option, selected_option == question.correct_option
        )
        all_answers = prior + (answered,)
        next_item = diagnostic_v1.select_next_question(all_answers)
        results = None
        if next_item is None:
            scored = [
                diagnostic_v1.score_domain(domain, all_answers)
                for domain in diagnostic_v1.DiagnosticDomain
            ]
            results = [
                {"domain": row.domain.value, "score": row.score,
                 "confidence": row.confidence, "response_count": row.response_count,
                 "reason_codes": list(row.reason_codes),
                 "scoring_policy_version": diagnostic_v1.SCORING_POLICY_VERSION}
                for row in scored
            ]
        try:
            updated = await self._repository.record_answer_v1(
                session_id=session_id, owner=owner, question_id=question_id,
                selected_option=selected_option, domain=question.domain.value,
                difficulty=question.difficulty, is_correct=answered.is_correct,
                next_question_id=next_item.question_id if next_item else None,
                results=results)
        except DiagnosticRepositoryError as exc:
            raise DiagnosticConflict("Diagnostic answer was not accepted") from exc
        payload = self._session_payload(updated)
        if results is not None:
            payload["results"] = results
            payload["intelligence_profile"] = await self._students.get_student_intelligence_v2(owner)
        return payload

    async def abandon(self, owner: str, session_id: str) -> None:
        if await self._repository.abandon(owner, session_id) is None:
            raise DiagnosticNotFound("Diagnostic session not found")

    async def latest_results(self, owner: str, study_plan_id: str) -> tuple[tuple[DiagnosticDomainResult, ...], str | None, datetime | None]:
        session, rows = await self._repository.latest_completed(owner, study_plan_id, ASSESSMENT_VERSION)
        if session is None:
            return (), None, None
        results = tuple(DiagnosticDomainResult(DiagnosticDomain(row["domain"]), int(row["score"]),
                                               row["confidence"], int(row["response_count"]),
                                               tuple(row["reason_codes"]),
                                               tuple(row.get("reasoning_patterns") or ())) for row in rows)
        return results, session["assessment_version"], datetime.fromisoformat(session["completed_at"].replace("Z", "+00:00"))

    async def _owned_session(self, owner: str, session_id: str) -> dict[str, object]:
        session = await self._repository.load_session(owner, session_id)
        if session is None:
            raise DiagnosticNotFound("Diagnostic session not found")
        return session

    @staticmethod
    def _session_payload(session: dict[str, object]) -> dict[str, object]:
        qid = session.get("current_question_id")
        if session["assessment_version"] == diagnostic_v1.ASSESSMENT_VERSION:
            question = diagnostic_v1.public_question(
                diagnostic_v1.QUESTIONS_BY_ID[str(qid)]) if qid else None
            maximum_questions = diagnostic_v1.MAX_QUESTIONS
        elif session["assessment_version"] == ASSESSMENT_VERSION:
            question = public_question(QUESTIONS_BY_ID[str(qid)]) if qid else None
            maximum_questions = TARGET_QUESTIONS
        else:
            raise DiagnosticConflict("Unsupported diagnostic assessment version")
        return {"session_id": session["id"], "status": session["status"],
                "assessment_version": session["assessment_version"],
                "answered_count": session["question_count"], "maximum_questions": maximum_questions,
                "question": question}
