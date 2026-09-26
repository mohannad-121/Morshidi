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

from typing import Any, Protocol, Sequence
from uuid import UUID
import httpx

from .enums import PolicyErrorCode
from .errors import PolicyRetrievalError


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


class StudentPolicyService:
    """Domain service orchestrating read-only student institutional policy queries."""

    def __init__(self, storage: PolicyReadStorage) -> None:
        self._storage = storage

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
