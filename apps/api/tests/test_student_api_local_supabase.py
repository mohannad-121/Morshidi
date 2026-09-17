"""Opt-in authenticated E2E against local Supabase and the real FastAPI app."""

import os
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

URL = os.getenv("MORSHIDI_LOCAL_SUPABASE_URL")
SERVER_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_SERVER_KEY")
ANON_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_ANON_KEY")
PLAN = os.getenv("MORSHIDI_LOCAL_STUDY_PLAN_ID")
pytestmark = pytest.mark.skipif(
    not all((URL, SERVER_KEY, ANON_KEY, PLAN)),
    reason="set local-only MORSHIDI_LOCAL_SUPABASE_* values",
)


def test_local_authenticated_student_api_end_to_end() -> None:
    password = f"Local-{uuid.uuid4()}-Aa1!"
    emails = [f"phase64-{uuid.uuid4()}@local.test", f"phase64-{uuid.uuid4()}@local.test"]
    admin_headers = {"apikey": SERVER_KEY or "", "Authorization": f"Bearer {SERVER_KEY or ''}"}
    user_ids: list[str] = []
    tokens: list[str] = []
    with httpx.Client(timeout=10) as local:
        try:
            for email in emails:
                created = local.post(f"{URL}/auth/v1/admin/users", headers=admin_headers,
                    json={"email": email, "password": password, "email_confirm": True})
                created.raise_for_status(); user_ids.append(created.json()["id"])
                signed_in = local.post(f"{URL}/auth/v1/token", params={"grant_type": "password"},
                    headers={"apikey": ANON_KEY or ""}, json={"email": email, "password": password})
                signed_in.raise_for_status(); tokens.append(signed_in.json()["access_token"])

            auth_a = {"Authorization": f"Bearer {tokens[0]}"}
            auth_b = {"Authorization": f"Bearer {tokens[1]}"}
            with TestClient(app) as client:
                created_profile = client.post("/api/v1/me/academic-profile", headers=auth_a,
                    json={"study_plan_id": PLAN, "reported_cumulative_gpa": 3.25,
                        "reported_gpa_scale": 4, "reported_earned_credit_hours": 15})
                assert created_profile.status_code == 201
                passed = client.post("/api/v1/me/academic-profile/attempts", headers=auth_a,
                    json={"course_code": "1501110", "status": "PASSED", "raw_grade_text": "B+"})
                assert passed.status_code == 201
                passed_id = passed.json()["id"]
                assert client.get("/api/v1/me/eligibility/1501112", headers=auth_a).json()["decision"] == "ELIGIBLE"

                referenced = client.post("/api/v1/me/academic-profile/attempts", headers=auth_a,
                    json={"course_code": "0300103", "status": "PASSED"})
                assert referenced.status_code == 201
                failed = client.post("/api/v1/me/academic-profile/attempts", headers=auth_a,
                    json={"course_code": "1501110", "status": "FAILED"})
                assert failed.status_code == 201
                failed_id = failed.json()["id"]
                listed = client.get("/api/v1/me/academic-profile/attempts", headers=auth_a)
                assert listed.status_code == 200
                assert "0300103" in {row["course_code"] for row in listed.json()}
                assert client.get("/api/v1/me/eligibility/1501112", headers=auth_a).json()["decision"] == "ELIGIBLE"
                assert client.patch(f"/api/v1/me/academic-profile/attempts/{passed_id}", headers=auth_a,
                    json={"raw_grade_text": "A-"}).status_code == 200
                assert client.delete(f"/api/v1/me/academic-profile/attempts/{failed_id}", headers=auth_a).status_code == 204

                assert client.get("/api/v1/me/academic-profile", headers=auth_b).status_code == 404
                assert client.patch(f"/api/v1/me/academic-profile/attempts/{passed_id}", headers=auth_b,
                    json={"status": "FAILED"}).status_code == 404

                rls_headers_b = {"apikey": ANON_KEY or "", "Authorization": f"Bearer {tokens[1]}"}
                assert local.get(f"{URL}/rest/v1/student_academic_profiles", headers=rls_headers_b,
                    params={"select": "id", "owner_user_id": f"eq.{user_ids[0]}"}).json() == []

                assert client.delete("/api/v1/me/academic-profile", headers=auth_a).status_code == 204
                remaining = local.get(f"{URL}/rest/v1/student_course_attempts", headers=admin_headers,
                    params={"select": "id", "id": f"eq.{passed_id}"})
                remaining.raise_for_status(); assert remaining.json() == []
        finally:
            for user_id in user_ids:
                local.delete(f"{URL}/auth/v1/admin/users/{user_id}", headers=admin_headers)
