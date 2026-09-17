"""Opt-in authenticated E2E against local Supabase and the real FastAPI app."""

import os
import uuid
from decimal import Decimal

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
                assert client.get("/api/v1/me/academic-profile", headers=auth_a).json()["id"] == created_profile.json()["id"]

                failed = client.post("/api/v1/me/academic-profile/attempts", headers=auth_a,
                    json={"course_code": "1501110", "status": "FAILED", "raw_grade_text": "raw-failure"})
                assert failed.status_code == 201
                failed_id = failed.json()["id"]
                failed_eligibility = client.get("/api/v1/me/eligibility/1501112", headers=auth_a)
                assert failed_eligibility.status_code == 200
                assert failed_eligibility.json()["decision"] == "NOT_ELIGIBLE"

                passed = client.post("/api/v1/me/academic-profile/attempts", headers=auth_a,
                    json={"course_code": "1501110", "status": "PASSED", "raw_grade_text": "B+"})
                assert passed.status_code == 201
                passed_id = passed.json()["id"]
                eligibility_one = client.get("/api/v1/me/eligibility/1501112", headers=auth_a)
                eligibility_two = client.get("/api/v1/me/eligibility/1501112", headers=auth_a)
                assert eligibility_one.status_code == 200
                assert eligibility_one.json() == eligibility_two.json()
                assert eligibility_one.json()["decision"] == "ELIGIBLE"

                referenced = client.post("/api/v1/me/academic-profile/attempts", headers=auth_a,
                    json={"course_code": "0300103", "status": "PASSED"})
                assert referenced.status_code == 201
                referenced_id = referenced.json()["id"]
                listed = client.get("/api/v1/me/academic-profile/attempts", headers=auth_a)
                assert listed.status_code == 200
                assert "0300103" in {row["course_code"] for row in listed.json()}
                assert [row["course_code"] for row in listed.json()].count("1501110") == 2

                progress_one = client.get("/api/v1/me/academic-progress", headers=auth_a)
                progress_two = client.get("/api/v1/me/academic-progress", headers=auth_a)
                assert progress_one.status_code == 200
                assert progress_one.json() == progress_two.json()
                assert Decimal(progress_one.json()["plan_total_required_credits"]) == 132
                assert Decimal(progress_one.json()["completed_plan_credits"]) == 3
                assert Decimal(progress_one.json()["reported_earned_credit_hours"]) == 15
                assert "0300103" not in {row["course_code"] for row in progress_one.json()["courses"]}

                updated_profile = client.patch("/api/v1/me/academic-profile", headers=auth_a,
                    json={"reported_cumulative_gpa": 3.5, "reported_gpa_scale": 4,
                        "reported_earned_credit_hours": 18})
                assert updated_profile.status_code == 200
                updated_progress = client.get("/api/v1/me/academic-progress", headers=auth_a).json()
                assert Decimal(updated_progress["reported_cumulative_gpa"]) == Decimal("3.5")
                assert Decimal(updated_progress["reported_gpa_scale"]) == 4
                assert Decimal(updated_progress["reported_earned_credit_hours"]) == 18
                assert Decimal(updated_progress["completed_plan_credits"]) == 3

                assert client.patch(f"/api/v1/me/academic-profile/attempts/{passed_id}", headers=auth_a,
                    json={"raw_grade_text": "A-"}).status_code == 200

                assert client.get("/api/v1/me/academic-profile", headers=auth_b).status_code == 404
                assert client.get("/api/v1/me/academic-progress", headers=auth_b).status_code == 404
                assert client.patch(f"/api/v1/me/academic-profile/attempts/{passed_id}", headers=auth_b,
                    json={"status": "FAILED"}).status_code == 404

                rls_headers_a = {"apikey": ANON_KEY or "", "Authorization": f"Bearer {tokens[0]}"}
                rls_headers_b = {"apikey": ANON_KEY or "", "Authorization": f"Bearer {tokens[1]}"}
                anon_headers = {"apikey": ANON_KEY or ""}
                assert len(local.get(f"{URL}/rest/v1/student_academic_profiles", headers=rls_headers_a,
                    params={"select": "id", "owner_user_id": f"eq.{user_ids[0]}"}).json()) == 1
                assert len(local.get(f"{URL}/rest/v1/student_course_attempts", headers=rls_headers_a,
                    params={"select": "id"}).json()) == 3
                assert local.get(f"{URL}/rest/v1/student_academic_profiles", headers=rls_headers_b,
                    params={"select": "id", "owner_user_id": f"eq.{user_ids[0]}"}).json() == []
                assert local.get(f"{URL}/rest/v1/student_course_attempts", headers=rls_headers_b,
                    params={"select": "id", "id": f"eq.{passed_id}"}).json() == []
                rls_mutation = local.patch(f"{URL}/rest/v1/student_course_attempts", headers={
                    **rls_headers_b, "Prefer": "return=representation"},
                    params={"id": f"eq.{passed_id}"}, json={"outcome": "WITHDRAWN"})
                rls_mutation.raise_for_status()
                assert rls_mutation.json() == []
                assert local.get(f"{URL}/rest/v1/student_academic_profiles", headers=anon_headers,
                    params={"select": "id"}).status_code in (401, 403)

                assert client.delete(f"/api/v1/me/academic-profile/attempts/{failed_id}", headers=auth_a).status_code == 204

                assert client.delete("/api/v1/me/academic-profile", headers=auth_a).status_code == 204
                remaining = local.get(f"{URL}/rest/v1/student_course_attempts", headers=admin_headers,
                    params={"select": "id", "id": f"in.({passed_id},{referenced_id})"})
                remaining.raise_for_status(); assert remaining.json() == []
        finally:
            for user_id in user_ids:
                local.delete(f"{URL}/auth/v1/admin/users/{user_id}", headers=admin_headers)
