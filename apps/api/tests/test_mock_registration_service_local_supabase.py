"""Opt-in real Auth -> FastAPI -> service -> P6.2 -> P6.4 integration."""

from __future__ import annotations

import os
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app

URL = os.getenv("MORSHIDI_LOCAL_SUPABASE_URL")
SERVER_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_SERVER_KEY")
ANON_KEY = os.getenv("MORSHIDI_LOCAL_SUPABASE_ANON_KEY")
pytestmark = pytest.mark.skipif(not all((URL, SERVER_KEY, ANON_KEY)),
    reason="set local-only MORSHIDI_LOCAL_SUPABASE_* values")


def _server_headers():
    return {"apikey": SERVER_KEY, "Authorization": f"Bearer {SERVER_KEY}",
            "Content-Type": "application/json", "Prefer": "return=representation"}


def _create_user(client, email, password):
    response = client.post(f"{URL}/auth/v1/admin/users", headers=_server_headers(),
        json={"email": email, "password": password, "email_confirm": True})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _token(client, email, password):
    response = client.post(f"{URL}/auth/v1/token?grant_type=password",
        headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_p6_5_real_authenticated_service_api_and_aggregate_pipeline():
    marker = uuid4().hex
    student_email = f"p65-student-{marker}@synthetic.invalid"
    analyst_email = f"p65-analyst-{marker}@synthetic.invalid"
    password = "Synthetic-only-P6.5-password!"
    with httpx.Client(timeout=30) as raw:
        rows = raw.get(f"{URL}/rest/v1/study_plan_courses", headers=_server_headers(), params={
            "select": "study_plan_id,course_id,prerequisite_logic_status,courses(course_code)",
            "prerequisite_logic_status": "eq.not_applicable", "limit": "1"}).json()
        assert rows
        plan_id, course_code = rows[0]["study_plan_id"], rows[0]["courses"]["course_code"]
        plan = raw.get(f"{URL}/rest/v1/study_plans", headers=_server_headers(), params={
            "select": "id,majors(faculties(university_id))", "id": f"eq.{plan_id}"}).json()[0]
        university_id = plan["majors"]["faculties"]["university_id"]
        student_id = _create_user(raw, student_email, password)
        analyst_id = _create_user(raw, analyst_email, password)
        assert raw.post(f"{URL}/rest/v1/student_academic_profiles", headers=_server_headers(),
            json={"owner_user_id": student_id, "study_plan_id": plan_id}).status_code == 201
        period_rows = raw.post(f"{URL}/rest/v1/mock_registration_target_periods",
            headers=_server_headers(), json={"university_id": university_id,
                "provider_namespace": "synthetic-p65", "period_key": marker,
                "period_class": "SYNTHETIC_SANDBOX_PERIOD",
                "verified_provider_source": False, "source_version": "synthetic-p65:v1"}).json()
        period_id = period_rows[0]["id"]
        assert raw.post(f"{URL}/rest/v1/institutional_memberships", headers=_server_headers(),
            json={"subject_user_id": analyst_id, "university_id": university_id,
                "provider_namespace": "synthetic-p65", "role": "INSTITUTIONAL_ANALYST",
                "active": True, "authority_source": "synthetic-test",
                "authority_source_version": "v1"}).status_code == 201
        student_token = _token(raw, student_email, password)
        analyst_token = _token(raw, analyst_email, password)

    with TestClient(app) as client:
        student_auth = {"Authorization": f"Bearer {student_token}"}
        body = {"target_period_id": period_id, "course_codes": [course_code],
                "expected_current_revision": None,
                "transparency_notice_version": "synthetic-notice:v1"}
        created = client.post("/api/v1/me/mock-registration/revisions",
                              headers=student_auth, json=body)
        assert created.status_code == 201, created.text
        assert created.json()["revision"] == 1
        replay = client.post("/api/v1/me/mock-registration/revisions",
                             headers=student_auth, json=body)
        assert replay.status_code == 201 and replay.json()["idempotent_replay"] is True
        current = client.get("/api/v1/me/mock-registration/current", headers=student_auth,
                             params={"target_period_id": period_id})
        assert current.status_code == 200 and current.json()["current_validity"] == "CURRENT_VALID"
        stale = dict(body, expected_current_revision=99)
        conflict = client.post("/api/v1/me/mock-registration/revisions",
                               headers=student_auth, json=stale)
        assert conflict.status_code == 409 and conflict.json()["error_code"] == "REVISION_CONFLICT"
        demand_params = {"university_id": university_id, "target_period_id": period_id}
        denied = client.get("/api/v1/institutional/demand", headers=student_auth,
                            params=demand_params)
        assert denied.status_code == 403
        aggregate = client.get("/api/v1/institutional/demand",
            headers={"Authorization": f"Bearer {analyst_token}"}, params=demand_params)
        assert aggregate.status_code == 200, aggregate.text
        payload = aggregate.json()
        assert payload["status"] == "SUPPRESSED" and payload["metrics"] == []
        assert "owner_user_id" not in str(payload)
        withdrawn = client.post("/api/v1/me/mock-registration/withdrawals",
            headers=student_auth, json={"target_period_id": period_id,
                "expected_current_revision": 1,
                "transparency_notice_version": "synthetic-notice:v1"})
        assert withdrawn.status_code == 201 and withdrawn.json()["lifecycle_status"] == "WITHDRAWN"
