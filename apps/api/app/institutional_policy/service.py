"""Phase P8: Read-Only Student Institutional Policy Service (WC-038).

AI EXPLAINS — DETERMINISTIC RULES DECIDE.
Read-only surface for students to access verified university regulations and institutional policies.
Enforces:
- Strict university-level tenant isolation.
- Showing only VERIFIED policy versions to students.
- Preserving exact source citations, locators, article numbers, and versions.
- Zero client bypass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence
from uuid import UUID
import httpx

from .enums import PolicyErrorCode
from .errors import PolicyRetrievalError
from .embeddings import PolicyEmbeddingError, PolicyEmbeddingProvider
from .query import CONCEPTS_BY_NAME, PolicyQueryPlan, _matches, normalize_policy_query, plan_policy_query


@dataclass(frozen=True, slots=True)
class PolicySearchOutcome:
    """Rows plus explicit retrieval diagnostics for grounded-answer callers."""

    rows: tuple[dict[str, Any], ...]
    retrieval_mode: str
    query_plan: PolicyQueryPlan
    fallback_reason: str | None = None


class PolicyReadStorage(Protocol):
    """Storage protocol for reading verified institutional policies."""

    async def list_verified_documents(
        self, university_id: str | UUID
    ) -> Sequence[dict[str, Any]]:
        ...

    async def get_document_detail(
        self, university_id: str | UUID, document_id: str | UUID
    ) -> dict[str, Any] | None:
        ...

    async def search_verified_passages(
        self, university_id: str | UUID, query: str, limit: int, category: str | None = None,
        document_id: str | None = None,
    ) -> Sequence[dict[str, Any]]:
        ...

    async def search_semantic_passages(
        self, university_id: str | UUID, embedding: Sequence[float], provider: str, model: str,
        limit: int, category: str | None = None, document_id: str | None = None,
    ) -> Sequence[dict[str, Any]]:
        ...


class InMemoryPolicyReadStorage:
    """In-memory storage adapter for testing policy read workflows."""

    def __init__(
        self,
        documents: Sequence[dict[str, Any]] | None = None,
        versions: Sequence[dict[str, Any]] | None = None,
        passages: Sequence[dict[str, Any]] | None = None,
    ) -> None:
        self.documents = list(documents or [])
        self.versions = list(versions or [])
        self.passages = list(passages or [])

    async def list_verified_documents(
        self, university_id: str | UUID
    ) -> Sequence[dict[str, Any]]:
        univ_str = str(university_id)
        results = []
        for doc in self.documents:
            if doc.get("university_id") != univ_str:
                continue
            # Check if there is a verified version
            doc_versions = [
                v for v in self.versions
                if v.get("document_id") == doc["id"] and v.get("status", "").lower() == "verified"
            ]
            if not doc_versions:
                continue
            active_version = doc_versions[0]
            passage_count = sum(1 for p in self.passages if p.get("version_id") == active_version["id"])
            results.append({
                "id": doc["id"],
                "university_id": doc["university_id"],
                "document_code": doc["document_code"],
                "title": doc["title"],
                "authority_level": doc["authority_level"],
                "category": doc["category"],
                "language": doc.get("language", "ar"),
                "active_version_tag": active_version["version_tag"],
                "effective_start_date": active_version.get("effective_start_date"),
                "passage_count": passage_count,
            })
        return results

    async def get_document_detail(
        self, university_id: str | UUID, document_id: str | UUID
    ) -> dict[str, Any] | None:
        univ_str = str(university_id)
        doc_str = str(document_id)
        matching_docs = [
            d for d in self.documents
            if d.get("id") == doc_str and d.get("university_id") == univ_str
        ]
        if not matching_docs:
            return None
        doc = matching_docs[0]
        doc_versions = [
            v for v in self.versions
            if v.get("document_id") == doc_str and v.get("status", "").lower() == "verified"
        ]
        if not doc_versions:
            return None
        active_version = doc_versions[0]
        version_passages = [
            p for p in self.passages
            if p.get("version_id") == active_version["id"]
        ]
        version_passages.sort(key=lambda p: p.get("sequence_order", 0))

        return {
            "id": doc["id"],
            "university_id": doc["university_id"],
            "document_code": doc["document_code"],
            "title": doc["title"],
            "authority_level": doc["authority_level"],
            "category": doc["category"],
            "language": doc.get("language", "ar"),
            "active_version": {
                "id": active_version["id"],
                "version_tag": active_version["version_tag"],
                "status": active_version["status"],
                "effective_start_date": active_version.get("effective_start_date"),
                "effective_end_date": active_version.get("effective_end_date"),
                "content_sha256": active_version.get("content_sha256"),
                "verified_at": active_version.get("verified_at"),
                "verified_by": active_version.get("verified_by"),
                "source_url": active_version.get("source_url"),
            },
            "passages": version_passages,
        }

    async def search_verified_passages(self, university_id: str | UUID, query: str, limit: int, category: str | None = None, document_id: str | None = None) -> Sequence[dict[str, Any]]:
        tokens = tuple(token for token in " ".join(query.lower().split()).split(" ") if len(token) >= 2)
        rows: list[dict[str, Any]] = []
        for detail in [await self.get_document_detail(university_id, str(doc["id"])) for doc in self.documents]:
            if not detail or (category and detail["category"] != category) or (document_id and detail["id"] != document_id):
                continue
            for passage in detail["passages"]:
                searchable = " ".join(str(passage.get(key) or "") for key in ("passage_text", "locator_text", "article_number", "section_number", "heading")).lower() + " " + detail["title"].lower() + " " + detail["document_code"].lower()
                score = (100 if " ".join(query.lower().split()) in searchable else 0) + 10 * sum(token in searchable for token in tokens)
                if score:
                    rows.append({"document_id": detail["id"], "document_code": detail["document_code"], "document_title": detail["title"], "category": detail["category"], "version_id": detail["active_version"]["id"], "version_tag": detail["active_version"]["version_tag"], **detail["active_version"], "passage_id": passage["id"], **passage, "score": score})
        return sorted(rows, key=lambda row: (-row["score"], row["document_code"], row["sequence_order"], row["passage_id"]))[:limit]

    async def search_semantic_passages(self, university_id: str | UUID, embedding: Sequence[float], provider: str, model: str, limit: int, category: str | None = None, document_id: str | None = None) -> Sequence[dict[str, Any]]:
        return []


class SupabasePolicyReadStorage:
    """Supabase PostgREST adapter for reading verified institutional policies."""

    def __init__(
        self,
        supabase_url: str,
        server_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._supabase_url = supabase_url.rstrip("/")
        self._server_key = server_key
        self._rest_url = f"{self._supabase_url}/rest/v1"
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        if not self._external_client:
            await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self._server_key,
            "Authorization": f"Bearer {self._server_key}",
        }

    async def list_verified_documents(
        self, university_id: str | UUID
    ) -> Sequence[dict[str, Any]]:
        univ_str = str(university_id)
        # Query verified policy documents for the university
        url = f"{self._rest_url}/policy_documents"
        params = {
            "select": "id,university_id,document_code,title,authority_level,category,language,policy_document_versions(id,version_tag,status,effective_start_date,effective_end_date,policy_passages(id))",
            "university_id": f"eq.{univ_str}",
            "policy_document_versions.status": "eq.verified",
            "order": "document_code.asc",
        }
        resp = await self._client.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        rows = resp.json()

        results = []
        for r in rows:
            versions = r.get("policy_document_versions") or []
            # Keep only verified versions
            verified_versions = [v for v in versions if v.get("status") == "verified"]
            if not verified_versions:
                continue
            active_v = verified_versions[0]
            passages = active_v.get("policy_passages") or []
            results.append({
                "id": r["id"],
                "university_id": r["university_id"],
                "document_code": r["document_code"],
                "title": r["title"],
                "authority_level": r["authority_level"],
                "category": r["category"],
                "language": r.get("language", "ar"),
                "active_version_tag": active_v["version_tag"],
                "effective_start_date": active_v.get("effective_start_date"),
                "passage_count": len(passages),
            })
        return results

    async def get_document_detail(
        self, university_id: str | UUID, document_id: str | UUID
    ) -> dict[str, Any] | None:
        univ_str = str(university_id)
        doc_str = str(document_id)

        url = f"{self._rest_url}/policy_documents"
        params = {
            "select": "id,university_id,document_code,title,authority_level,category,language,policy_document_versions(id,version_tag,status,effective_start_date,effective_end_date,content_sha256,verified_at,verified_by,source_url,source_snapshot_ref)",
            "id": f"eq.{doc_str}",
            "university_id": f"eq.{univ_str}",
            "policy_document_versions.status": "eq.verified",
        }
        resp = await self._client.get(url, headers=self._headers(), params=params)
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            return None

        doc = rows[0]
        versions = doc.get("policy_document_versions") or []
        verified_versions = [v for v in versions if v.get("status") == "verified"]
        if not verified_versions:
            return None

        active_v = verified_versions[0]
        v_id = active_v["id"]

        # Fetch passages ordered by sequence_order
        p_url = f"{self._rest_url}/policy_passages"
        p_params = {
            "select": "id,version_id,passage_text,locator_text,article_number,section_number,page_number,heading,sequence_order,passage_sha256",
            "version_id": f"eq.{v_id}",
            "order": "sequence_order.asc",
        }
        p_resp = await self._client.get(p_url, headers=self._headers(), params=p_params)
        p_resp.raise_for_status()
        passages = p_resp.json()

        return {
            "id": doc["id"],
            "university_id": doc["university_id"],
            "document_code": doc["document_code"],
            "title": doc["title"],
            "authority_level": doc["authority_level"],
            "category": doc["category"],
            "language": doc.get("language", "ar"),
            "active_version": active_v,
            "passages": passages,
        }

    async def search_verified_passages(self, university_id: str | UUID, query: str, limit: int, category: str | None = None, document_id: str | None = None) -> Sequence[dict[str, Any]]:
        response = await self._client.post(
            f"{self._rest_url}/rpc/search_verified_policy_passages",
            headers=self._headers(),
            json={"p_university_id": str(university_id), "p_query": query, "p_limit": limit, "p_category": category, "p_document_id": document_id},
        )
        response.raise_for_status()
        return response.json()

    async def search_semantic_passages(self, university_id: str | UUID, embedding: Sequence[float], provider: str, model: str, limit: int, category: str | None = None, document_id: str | None = None) -> Sequence[dict[str, Any]]:
        response = await self._client.post(
            f"{self._rest_url}/rpc/search_verified_policy_passages_semantic",
            headers=self._headers(),
            json={"p_university_id": str(university_id), "p_query_embedding": list(embedding), "p_provider": provider, "p_model": model, "p_limit": limit, "p_category": category, "p_document_id": document_id},
        )
        response.raise_for_status()
        return response.json()


class StudentPolicyService:
    """Domain service orchestrating read-only student institutional policy queries."""

    def __init__(self, storage: PolicyReadStorage, embedding_provider: PolicyEmbeddingProvider | None = None) -> None:
        self._storage = storage
        self._embedding_provider = embedding_provider

    async def list_policies_for_student(
        self, university_id: str | UUID
    ) -> Sequence[dict[str, Any]]:
        return await self._storage.list_verified_documents(university_id)

    async def get_policy_detail_for_student(
        self, university_id: str | UUID, document_id: str | UUID
    ) -> dict[str, Any]:
        detail = await self._storage.get_document_detail(university_id, document_id)
        if detail is None:
            raise PolicyRetrievalError(
                PolicyErrorCode.DOCUMENT_NOT_FOUND,
                f"Policy document {document_id} was not found for this university",
            )
        return detail

    async def search_policies_for_student(self, university_id: str | UUID, query: str, limit: int, category: str | None = None, document_id: str | None = None, mode: str = "lexical") -> Sequence[dict[str, Any]]:
        outcome = await self.search_policies_with_diagnostics(
            university_id, query, limit, category, document_id, mode
        )
        return outcome.rows

    async def search_policies_with_diagnostics(
        self, university_id: str | UUID, query: str, limit: int,
        category: str | None = None, document_id: str | None = None,
        mode: str = "lexical",
    ) -> PolicySearchOutcome:
        if mode not in {"lexical", "semantic", "hybrid"}:
            raise ValueError("unsupported policy retrieval mode")
        if not 1 <= limit <= 20:
            raise ValueError("policy retrieval limit must be between 1 and 20")
        plan = plan_policy_query(query)
        candidate_limit = min(20, max(limit * 2, limit))
        lexical: list[dict[str, Any]] = []
        if mode != "semantic":
            lexical_lists = [
                await self._storage.search_verified_passages(
                    university_id, variant, candidate_limit, category, document_id
                )
                for variant in plan.lexical_queries
            ]
            lexical = _fuse_lexical_variants(lexical_lists, candidate_limit, plan)
            if mode == "lexical":
                return PolicySearchOutcome(tuple(lexical[:limit]), "lexical", plan)

        if self._embedding_provider is None:
            if mode == "semantic":
                raise PolicyEmbeddingError("policy.embedding.not_configured")
            return PolicySearchOutcome(
                tuple(lexical[:limit]), "lexical_fallback", plan,
                "policy.embedding.not_configured",
            )
        try:
            vector = await self._embedding_provider.embed_query(plan.normalized_text)
            semantic = await self._storage.search_semantic_passages(
                university_id, vector, self._embedding_provider.model.provider,
                self._embedding_provider.model.model, candidate_limit, category, document_id,
            )
        except (PolicyEmbeddingError, httpx.HTTPError) as exc:
            if mode == "semantic":
                raise
            return PolicySearchOutcome(
                tuple(lexical[:limit]), "lexical_fallback", plan,
                _safe_fallback_reason(exc),
            )
        if mode == "semantic":
            return PolicySearchOutcome(tuple(_deduplicate_evidence(semantic)[:limit]), "semantic", plan)
        return PolicySearchOutcome(
            tuple(_fuse_policy_results(lexical, semantic, limit, plan)), "hybrid", plan
        )


def _safe_fallback_reason(error: Exception) -> str:
    if isinstance(error, PolicyEmbeddingError) and str(error).startswith("policy.embedding."):
        return str(error)
    return "policy.embedding.unavailable"


def _evidence_key(row: dict[str, Any]) -> tuple[str, ...]:
    passage_id = str(row.get("passage_id") or "")
    content_hash = str(row.get("passage_sha256") or "")
    if content_hash:
        return (
            str(row.get("document_id") or ""), str(row.get("version_id") or ""), content_hash,
        )
    return ("passage", passage_id)


def _deduplicate_evidence(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen_passages: set[str] = set()
    seen_evidence: set[tuple[str, ...]] = set()
    for row in rows:
        passage_id = str(row.get("passage_id") or "")
        evidence_key = _evidence_key(row)
        if not passage_id or passage_id in seen_passages or evidence_key in seen_evidence:
            continue
        seen_passages.add(passage_id)
        seen_evidence.add(evidence_key)
        unique.append(dict(row))
    return unique


def _intent_score(row: dict[str, Any], plan: PolicyQueryPlan) -> float:
    if not plan.concepts:
        return 0.0
    searchable = normalize_policy_query(" ".join(str(row.get(field) or "") for field in (
        "document_title", "category", "heading", "locator_text", "passage_text",
    )))
    matched = 0
    for concept_name in plan.concepts:
        concept = CONCEPTS_BY_NAME.get(concept_name)
        if concept is not None and any(_matches(searchable, trigger) for trigger in concept.triggers):
            matched += 1
    return min(1.0, matched / max(1, len(plan.concepts)))


def _fuse_lexical_variants(
    result_lists: Sequence[Sequence[dict[str, Any]]], limit: int, plan: PolicyQueryPlan,
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for variant_index, rows in enumerate(result_lists):
        variant_weight = 1.0 if variant_index == 0 else 0.75
        for rank, row in enumerate(rows, start=1):
            key = str(row.get("passage_id") or "")
            if not key:
                continue
            item = merged.setdefault(key, dict(row))
            item["lexical_rank"] = min(rank, int(item.get("lexical_rank") or rank))
            item["lexical_score"] = float(item.get("lexical_score", 0.0)) + variant_weight / (60 + rank)
    ranked = list(merged.values())
    for item in ranked:
        item["intent_score"] = _intent_score(item, plan)
    ranked.sort(key=lambda row: (
        -(float(row.get("lexical_score", 0.0)) + 0.002 * float(row.get("intent_score", 0.0))),
        str(row.get("document_code") or ""), int(row.get("sequence_order") or 0),
        str(row.get("passage_id") or ""),
    ))
    return _deduplicate_evidence(ranked)[:limit]


def _fuse_policy_results(lexical: Sequence[dict[str, Any]], semantic: Sequence[dict[str, Any]], limit: int, plan: PolicyQueryPlan | None = None) -> list[dict[str, Any]]:
    """Deterministic RRF fusion; evidence stays verbatim and appears once."""
    merged: dict[str, dict[str, Any]] = {}
    for rank, row in enumerate(lexical, start=1):
        item = dict(row)
        item["lexical_rank"] = rank
        item["semantic_rank"] = None
        item["semantic_similarity"] = None
        item["hybrid_score"] = 1 / (60 + rank)
        merged[str(row["passage_id"])] = item
    for rank, row in enumerate(semantic, start=1):
        key = str(row["passage_id"])
        item = merged.setdefault(key, dict(row))
        item["semantic_rank"] = rank
        item["semantic_similarity"] = row.get("semantic_similarity")
        item.setdefault("lexical_rank", None)
        item["hybrid_score"] = float(item.get("hybrid_score", 0)) + 1 / (60 + rank)
    if plan is not None:
        for item in merged.values():
            item["intent_score"] = _intent_score(item, plan)
            item["hybrid_score"] = float(item["hybrid_score"]) + 0.002 * item["intent_score"]
    ranked = sorted(merged.values(), key=lambda row: (-float(row.get("hybrid_score") or 0.0), str(row.get("document_code") or ""), int(row.get("sequence_order") or 0), str(row.get("passage_id") or "")))
    return _deduplicate_evidence(ranked)[:limit]
