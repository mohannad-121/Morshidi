from __future__ import annotations

from typing import Any

import httpx


class UniversityEventStore:
    def __init__(self, supabase_url: str, service_key: str, client: httpx.AsyncClient) -> None:
        self._rest = f"{supabase_url.rstrip('/')}/rest/v1"
        self._key = service_key
        self._client = client

    def _headers(self) -> dict[str, str]:
        return {"apikey": self._key, "Authorization": f"Bearer {self._key}", "Accept": "application/json"}

    async def ingest(self, university_id: str, event: dict[str, Any]) -> dict[str, Any]:
        response = await self._client.post(
            f"{self._rest}/rpc/ingest_university_event_scoped", headers={**self._headers(), "Content-Type": "application/json"},
            json={"p_university_id": university_id, "p_event": event}, timeout=5,
        )
        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, dict) else {"applied": False, "duplicate": False}

    async def list_notifications(self, university_id: str, student_id: str, since: str | None = None, *, after_id: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, str] = {
            "select": "id,event_id,student_id,summary,created_at",
            "university_id": f"eq.{university_id}",
            "or": f"(student_id.eq.{student_id},student_id.is.null)",
            "order": "created_at.desc,id.desc", "limit": "50",
        }
        if after_id is not None:
            params["id"] = f"gt.{after_id}"
            params["order"] = "id.asc"
        elif since:
            params["created_at"] = f"gt.{since}"
        response = await self._client.get(f"{self._rest}/student_notifications", params=params,
                                          headers=self._headers(), timeout=5)
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            return []
        return rows
