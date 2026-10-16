"""Service-role persistence adapter for owner-scoped diagnostic sessions."""

from __future__ import annotations

from typing import Any

import httpx


class DiagnosticRepositoryError(RuntimeError):
    pass


class SupabaseDiagnosticRepository:
    def __init__(self, base_url: str, service_key: str, client: httpx.AsyncClient) -> None:
        self._url = base_url.rstrip("/")
        self._client = client
        self._headers = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = await self._client.request(method, f"{self._url}{path}",
                                              headers={**self._headers, **kwargs.pop("headers", {})},
                                              timeout=10, **kwargs)
        if response.status_code >= 400:
            raise DiagnosticRepositoryError("Diagnostic persistence operation failed")
        return response

    async def load_active(self, owner: str, study_plan_id: str, version: str) -> dict[str, Any] | None:
        response = await self._request("GET", "/rest/v1/student_diagnostic_sessions", params={
            "select": "*", "owner_user_id": f"eq.{owner}", "study_plan_id": f"eq.{study_plan_id}",
            "assessment_version": f"eq.{version}", "status": "eq.IN_PROGRESS", "limit": "1"})
        rows = response.json()
        return rows[0] if rows else None

    async def load_session(self, owner: str, session_id: str) -> dict[str, Any] | None:
        response = await self._request("GET", "/rest/v1/student_diagnostic_sessions", params={
            "select": "*", "owner_user_id": f"eq.{owner}", "id": f"eq.{session_id}", "limit": "1"})
        rows = response.json()
        return rows[0] if rows else None

    async def create_session(self, owner: str, profile_id: str, institution_id: str,
                             study_plan_id: str, version: str, question_id: str) -> dict[str, Any]:
        response = await self._request("POST", "/rest/v1/student_diagnostic_sessions",
            headers={"Prefer": "return=representation"}, json={
                "owner_user_id": owner, "profile_id": profile_id, "institution_id": institution_id,
                "study_plan_id": study_plan_id, "assessment_version": version,
                "status": "IN_PROGRESS", "current_question_id": question_id})
        return response.json()[0]

    async def load_responses(self, session_id: str) -> list[dict[str, Any]]:
        response = await self._request("GET", "/rest/v1/student_diagnostic_responses", params={
            "select": "question_id,selected_option,is_correct,response_time_ms,self_confidence,response_order",
            "session_id": f"eq.{session_id}",
            "order": "response_order.asc"})
        return response.json()

    async def record_answer_v1(self, *, session_id: str, owner: str, question_id: str,
                               selected_option: str, domain: str, difficulty: str,
                               is_correct: bool, next_question_id: str | None,
                               results: list[dict[str, Any]] | None) -> dict[str, Any]:
        response = await self._request("POST", "/rest/v1/rpc/record_student_diagnostic_answer", json={
            "p_session_id": session_id, "p_owner_user_id": owner, "p_question_id": question_id,
            "p_selected_option": selected_option, "p_domain": domain, "p_difficulty": difficulty,
            "p_is_correct": is_correct, "p_next_question_id": next_question_id,
            "p_results": results})
        payload = response.json()
        return payload[0] if isinstance(payload, list) else payload

    async def record_answer_v2(self, *, session_id: str, owner: str, question_id: str,
                               selected_option: str, domain: str, difficulty: str, is_correct: bool,
                               response_time_ms: int, self_confidence: str,
                               next_question_id: str | None,
                               results: list[dict[str, Any]] | None) -> dict[str, Any]:
        response = await self._request("POST", "/rest/v1/rpc/record_student_diagnostic_answer", json={
            "p_session_id": session_id, "p_owner_user_id": owner, "p_question_id": question_id,
            "p_selected_option": selected_option, "p_domain": domain, "p_difficulty": difficulty,
            "p_is_correct": is_correct, "p_response_time_ms": response_time_ms,
            "p_self_confidence": self_confidence,
            "p_next_question_id": next_question_id, "p_results": results})
        payload = response.json()
        return payload[0] if isinstance(payload, list) else payload

    async def abandon(self, owner: str, session_id: str) -> dict[str, Any] | None:
        response = await self._request("PATCH", "/rest/v1/student_diagnostic_sessions", params={
            "owner_user_id": f"eq.{owner}", "id": f"eq.{session_id}", "status": "eq.IN_PROGRESS"},
            headers={"Prefer": "return=representation"},
            json={"status": "ABANDONED", "current_question_id": None})
        rows = response.json()
        return rows[0] if rows else None

    async def latest_completed(self, owner: str, study_plan_id: str, version: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        response = await self._request("GET", "/rest/v1/student_diagnostic_sessions", params={
            "select": "*", "owner_user_id": f"eq.{owner}", "study_plan_id": f"eq.{study_plan_id}",
            "assessment_version": f"eq.{version}", "status": "eq.COMPLETED",
            "order": "completed_at.desc,id.desc", "limit": "1"})
        rows = response.json()
        if not rows:
            return None, []
        session = rows[0]
        result = await self._request("GET", "/rest/v1/student_diagnostic_skill_results", params={
            "select": "domain,score,confidence,response_count,reason_codes,reasoning_patterns,scoring_policy_version",
            "session_id": f"eq.{session['id']}", "order": "domain.asc"})
        return session, result.json()
