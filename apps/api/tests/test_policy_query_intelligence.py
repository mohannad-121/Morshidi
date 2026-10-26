"""Evaluation matrix for deterministic policy-query understanding and retrieval."""

from __future__ import annotations

import httpx
import pytest

from app.institutional_policy.embeddings import EmbeddingModel, PolicyEmbeddingError
from app.institutional_policy.query import normalize_policy_query, plan_policy_query
from app.institutional_policy.service import StudentPolicyService, _fuse_policy_results


@pytest.mark.parametrize(("query", "intent"), [
    ("شو بصير إذا غبت كثير؟", "attendance"),
    ("كم غياب مسموح", "attendance"),
    ("What is the attendance policy?", "attendance"),
    ("I missed class twice", "attendance"),
    ("بدي أسحب المادة", "withdrawal"),
    ("كيف اسقط المساق؟", "withdrawal"),
    ("course withdrawal deadline", "withdrawal"),
    ("Can I drop course CS-101?", "withdrawal"),
    ("متى امتحان الفاينل", "examinations"),
    ("نظام الاختبارات", "examinations"),
    ("exam regulations", "examinations"),
    ("midterm policy", "examinations"),
    ("كيف بتنحسب العلامة؟", "grades"),
    ("شو التقدير للدرجة ٨٥", "grades"),
    ("grade appeal rules", "grades"),
    ("GPA policy", "grades"),
    ("متى بفتح التسجيل", "registration"),
    ("الشعبة مسكرة", "registration"),
    ("registration period", "registration"),
    ("enrollment regulation", "registration"),
    ("شو متطلبات التخرج", "graduation"),
    ("تعليمات التخرج", "graduation"),
    ("graduation requirements", "graduation"),
    ("degree requirement policy", "graduation"),
    ("بدي أعادل مادة", "transfer"),
    ("الساعات المنقولة", "transfer"),
    ("transfer credit policy", "transfer"),
    ("course equivalency", "transfer"),
    ("شو عقوبة المخالفة", "discipline"),
    ("نظام العقوبات", "discipline"),
    ("disciplinary penalty", "discipline"),
    ("academic misconduct rules", "discipline"),
    ("كم رسوم المادة", "fees"),
    ("وين أدفع المصاري", "fees"),
    ("tuition fees", "fees"),
    ("payment policy", "fees"),
    ("شو شروط الإنذار الأكاديمي؟", "academic_standing"),
    ("academic probation policy", "academic_standing"),
    ("كم الحد الأعلى للعبء الدراسي؟", "course_load"),
    ("maximum course load", "course_load"),
    ("بقدر أأجل الفصل؟", "postponement"),
    ("leave of absence policy", "postponement"),
    ("شو إجراءات العذر الطبي للامتحان؟", "incomplete"),
    ("make-up exam excuse", "incomplete"),
    ("بقدر أعيد مادة عشان أرفع معدلي؟", "course_repeat"),
    ("retake course policy", "course_repeat"),
    ("شروط اسقاط ماده", "withdrawal"),
    ("ما هي لوائح الجامعة؟", "general_policy"),
    ("university bylaws", "general_policy"),
    ("أريد النص الرسمي", "general_policy"),
    ("show the official policy", "general_policy"),
])
def test_policy_query_intent_evaluation_matrix(query: str, intent: str) -> None:
    plan = plan_policy_query(query)
    assert plan.intent == intent
    assert plan.lexical_queries
    assert len(plan.lexical_queries) <= 4


@pytest.mark.parametrize(("raw", "expected"), [
    ("  الإِنْسِحَابُ  ", "الانسحاب"),
    ("آلية إسقاط المادّة", "الية اسقاط المادة"),
    ("مادة ١٢٣٤", "مادة 1234"),
    ("CS-101 / الشُّعبة", "cs-101 الشعبة"),
    ("TRANSFER—CREDIT", "transfer credit"),
    ("رســوم\n\tالدفع", "رسوم الدفع"),
    ("متى؟ التسجيل!", "متي التسجيل"),
    ("إختبار FINAL", "اختبار final"),
])
def test_policy_normalization_evaluation_matrix(raw: str, expected: str) -> None:
    assert normalize_policy_query(raw) == expected


class RecordingStorage:
    def __init__(self, *, semantic_error: Exception | None = None) -> None:
        self.semantic_error = semantic_error
        self.lexical_calls: list[tuple] = []
        self.semantic_calls: list[tuple] = []

    async def list_verified_documents(self, university_id):
        return []

    async def get_document_detail(self, university_id, document_id):
        return None

    async def search_verified_passages(self, university_id, query, limit, category=None, document_id=None):
        self.lexical_calls.append((university_id, query, limit, category, document_id))
        return [{
            "passage_id": "p1", "document_id": "d1", "version_id": "v1",
            "passage_sha256": "a" * 64, "document_code": "POL", "sequence_order": 1,
            "document_title": "سياسة الغياب", "heading": "الغياب",
            "locator_text": "المادة 1", "passage_text": "تنظم هذه المادة الغياب.",
            "category": "academic_bylaws", "score": 10,
        }]

    async def search_semantic_passages(self, university_id, embedding, provider, model, limit, category=None, document_id=None):
        self.semantic_calls.append((university_id, provider, model, limit, category, document_id))
        if self.semantic_error:
            raise self.semantic_error
        return []


class Embeddings:
    model = EmbeddingModel("test", "test-model", 2)

    async def embed_query(self, text):
        return (0.1, 0.2)


@pytest.mark.anyio
async def test_hybrid_expands_queries_but_preserves_tenant_and_filters_on_every_call() -> None:
    storage = RecordingStorage()
    outcome = await StudentPolicyService(storage, Embeddings()).search_policies_with_diagnostics(
        "tenant-a", "شو بصير إذا غبت كثير؟", 3, "academic_bylaws", "doc-a", "hybrid"
    )
    assert outcome.retrieval_mode == "hybrid"
    assert outcome.query_plan.intent == "attendance"
    assert len(storage.lexical_calls) >= 2
    assert all(call[0] == "tenant-a" and call[3:] == ("academic_bylaws", "doc-a") for call in storage.lexical_calls)
    assert storage.semantic_calls == [("tenant-a", "test", "test-model", 6, "academic_bylaws", "doc-a")]


@pytest.mark.anyio
async def test_hybrid_without_embeddings_is_an_explicit_lexical_fallback() -> None:
    storage = RecordingStorage()
    outcome = await StudentPolicyService(storage).search_policies_with_diagnostics(
        "tenant-a", "attendance policy", 3, mode="hybrid"
    )
    assert outcome.retrieval_mode == "lexical_fallback"
    assert outcome.fallback_reason == "policy.embedding.not_configured"
    assert [row["passage_id"] for row in outcome.rows] == ["p1"]


@pytest.mark.anyio
@pytest.mark.parametrize("error", [
    PolicyEmbeddingError("policy.embedding.timeout"),
    httpx.ConnectError("offline"),
])
async def test_hybrid_vector_failure_falls_back_without_exposing_provider_details(error: Exception) -> None:
    class FailingEmbeddings(Embeddings):
        async def embed_query(self, text):
            raise error

    outcome = await StudentPolicyService(RecordingStorage(), FailingEmbeddings()).search_policies_with_diagnostics(
        "tenant-a", "attendance", 3, mode="hybrid"
    )
    assert outcome.retrieval_mode == "lexical_fallback"
    assert outcome.fallback_reason in {"policy.embedding.timeout", "policy.embedding.unavailable"}


@pytest.mark.anyio
async def test_semantic_only_remains_fail_closed_when_embeddings_are_missing() -> None:
    with pytest.raises(PolicyEmbeddingError, match="not_configured"):
        await StudentPolicyService(RecordingStorage()).search_policies_with_diagnostics(
            "tenant-a", "attendance", 3, mode="semantic"
        )


def test_hybrid_deduplicates_same_version_and_content_even_with_different_passage_ids() -> None:
    base = {
        "document_id": "d1", "version_id": "v1", "passage_sha256": "a" * 64,
        "document_code": "POL", "sequence_order": 1,
    }
    result = _fuse_policy_results(
        [{**base, "passage_id": "p1"}, {**base, "passage_id": "p2"}], [], 5
    )
    assert [row["passage_id"] for row in result] == ["p1"]


def test_hybrid_keeps_identical_content_from_distinct_versions_for_conflict_detection() -> None:
    base = {"passage_sha256": "a" * 64, "document_code": "POL", "sequence_order": 1}
    result = _fuse_policy_results([
        {**base, "document_id": "d1", "version_id": "v1", "passage_id": "p1"},
        {**base, "document_id": "d1", "version_id": "v2", "passage_id": "p2"},
    ], [], 5)
    assert [row["passage_id"] for row in result] == ["p1", "p2"]

