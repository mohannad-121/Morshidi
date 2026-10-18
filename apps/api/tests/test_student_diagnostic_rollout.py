import asyncio
from types import SimpleNamespace

import pytest

from app.student_intelligence import diagnostic_v1
from app.student_intelligence.diagnostic import ASSESSMENT_VERSION, QUESTIONS_BY_ID
from app.student_intelligence.diagnostic_service import DiagnosticConflict, DiagnosticService
from app.student_intelligence.taxonomy import PLAN12_ID


OWNER = "11111111-1111-1111-1111-111111111111"
SESSION = "22222222-2222-2222-2222-222222222222"


class StudentFake:
    async def get_profile(self, owner: str):
        assert owner == OWNER
        return SimpleNamespace(profile_id="profile", study_plan_id=PLAN12_ID)

    async def resolve_student_university_id(self, owner: str) -> str:
        assert owner == OWNER
        return "institution"

    async def get_student_intelligence_v2(self, owner: str):
        assert owner == OWNER
        return {"student_id": "student"}


class RepositoryFake:
    def __init__(self, version: str, question_id: str = "P01") -> None:
        self.session = {
            "id": SESSION, "owner_user_id": OWNER, "study_plan_id": PLAN12_ID,
            "assessment_version": version, "status": "IN_PROGRESS",
            "current_question_id": question_id, "question_count": 0,
        }
        self.calls: list[tuple[str, dict]] = []

    async def load_session(self, owner: str, session_id: str):
        return self.session if owner == OWNER and session_id == SESSION else None

    async def load_responses(self, session_id: str):
        assert session_id == SESSION
        return []

    async def record_answer_v1(self, **kwargs):
        self.calls.append(("V1", kwargs))
        return {**self.session, "question_count": 1,
                "current_question_id": kwargs["next_question_id"]}

    async def record_answer_v2(self, **kwargs):
        self.calls.append(("V2", kwargs))
        return {**self.session, "question_count": 1,
                "current_question_id": kwargs["next_question_id"]}

    async def load_active(self, owner: str, study_plan_id: str, version: str):
        if owner == OWNER and study_plan_id == PLAN12_ID and version == self.session["assessment_version"]:
            return self.session
        return None

    async def latest_completed(self, owner: str, study_plan_id: str, version: str):
        return None, []

    async def create_session(self, owner: str, profile_id: str, institution_id: str,
                             study_plan_id: str, version: str, question_id: str):
        self.session = {**self.session, "assessment_version": version,
                        "current_question_id": question_id}
        return self.session


def test_backend_uses_authoritative_v1_session_for_old_and_new_request_shapes() -> None:
    async def scenario() -> None:
        for timing, confidence in ((None, None), (12_000, "HIGH")):
            repository = RepositoryFake(diagnostic_v1.ASSESSMENT_VERSION)
            service = DiagnosticService(repository, StudentFake())
            payload = await service.answer(
                OWNER, SESSION, "P01", diagnostic_v1.QUESTIONS_BY_ID["P01"].correct_option,
                timing, confidence,
            )
            assert payload["assessment_version"] == diagnostic_v1.ASSESSMENT_VERSION
            assert payload["maximum_questions"] == diagnostic_v1.MAX_QUESTIONS
            assert payload["question"] is not None and "domain" in payload["question"]
            assert repository.calls[0][0] == "V1"
            assert "response_time_ms" not in repository.calls[0][1]
            assert "self_confidence" not in repository.calls[0][1]

    asyncio.run(scenario())


def test_v2_requires_evidence_and_uses_only_v2_rpc() -> None:
    async def scenario() -> None:
        repository = RepositoryFake(ASSESSMENT_VERSION)
        service = DiagnosticService(repository, StudentFake())
        with pytest.raises(DiagnosticConflict, match="V2 diagnostic evidence is required"):
            await service.answer(OWNER, SESSION, "P01", "A", None, None)
        assert repository.calls == []

        option = QUESTIONS_BY_ID["P01"].correct_option
        payload = await service.answer(OWNER, SESSION, "P01", option, 12_000, "HIGH")
        assert payload["assessment_version"] == ASSESSMENT_VERSION
        assert payload["maximum_questions"] == 30
        assert payload["question"] is not None and "domain" not in payload["question"]
        assert repository.calls[0][0] == "V2"
        assert repository.calls[0][1]["response_time_ms"] == 12_000
        assert repository.calls[0][1]["self_confidence"] == "HIGH"

    asyncio.run(scenario())


def test_unversioned_start_is_v1_v2_opt_in_is_v2_and_active_v1_wins() -> None:
    async def scenario() -> None:
        legacy_repository = RepositoryFake(diagnostic_v1.ASSESSMENT_VERSION)
        legacy_service = DiagnosticService(legacy_repository, StudentFake())
        assert (await legacy_service.start(OWNER))["assessment_version"] == diagnostic_v1.ASSESSMENT_VERSION
        assert (await legacy_service.start(OWNER, ASSESSMENT_VERSION))[
            "assessment_version"] == diagnostic_v1.ASSESSMENT_VERSION

        v2_repository = RepositoryFake(ASSESSMENT_VERSION)
        v2_service = DiagnosticService(v2_repository, StudentFake())
        assert (await v2_service.start(OWNER, ASSESSMENT_VERSION))["assessment_version"] == ASSESSMENT_VERSION

    asyncio.run(scenario())
