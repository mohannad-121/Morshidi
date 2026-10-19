from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.routes.institutional_analytics import _service
from app.core.auth import CurrentUser, get_current_user
from app.institutional_analytics.engine import build_dashboard, simulate_capacity
from app.institutional_analytics.service import InstitutionalAnalyticsError
from app.main import app
from tests.test_institutional_analytics import ADMIN_ID, UNIVERSITY_ID, snapshot


class AnalyticsStub:
    def __init__(self, denied: bool = False):
        self.denied = denied
        self.calls: list[tuple] = []

    async def access(self, subject):
        if self.denied:
            raise InstitutionalAnalyticsError("INSTITUTIONAL_ACCESS_DENIED", 403, "denied")
        self.calls.append(("access", subject))
        return [{"university_id": UNIVERSITY_ID, "role_scope": "INSTITUTION_ADMIN"}]

    async def dashboard(self, subject, **filters):
        if self.denied:
            raise InstitutionalAnalyticsError("INSTITUTIONAL_ACCESS_DENIED", 403, "denied")
        self.calls.append(("dashboard", subject, filters))
        return build_dashboard(snapshot(), minimum_cohort_size=3)

    async def simulate(self, subject, request):
        self.calls.append(("simulate", subject, request))
        dashboard = build_dashboard(snapshot(), minimum_cohort_size=3)
        course = next(item for item in dashboard.courses if item.course_code == request.course_code)
        return simulate_capacity(course, request)


def test_dashboard_routes_bind_verified_subject_and_are_private_no_store():
    service = AnalyticsStub()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(ADMIN_ID)
    app.dependency_overrides[_service] = lambda: service
    try:
        with TestClient(app) as client:
            access = client.get("/api/v1/institutional/analytics/access")
            assert access.status_code == 200
            response = client.get(
                "/api/v1/institutional/analytics/dashboard",
                params={"university_id": UNIVERSITY_ID, "term_key": "2026/2027-1", "faculty": "IT"},
            )
            assert response.status_code == 200
            assert response.headers["cache-control"] == "private, no-store"
            assert response.json()["kind"] == "INSTITUTIONAL_INTELLIGENCE_DASHBOARD"
            assert service.calls[-1][1] == ADMIN_ID
            assert service.calls[-1][2]["faculty"] == "IT"
    finally:
        app.dependency_overrides.clear()


def test_denied_role_returns_stable_403_without_aggregate_payload():
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(ADMIN_ID)
    app.dependency_overrides[_service] = lambda: AnalyticsStub(denied=True)
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/institutional/analytics/access")
            assert response.status_code == 403
            assert response.json() == {
                "kind": "error", "error_code": "INSTITUTIONAL_ACCESS_DENIED", "detail": "denied"}
    finally:
        app.dependency_overrides.clear()


def test_simulation_is_typed_non_mutating_and_rejects_arbitrary_fields():
    service = AnalyticsStub()
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(ADMIN_ID)
    app.dependency_overrides[_service] = lambda: service
    body = {"university_id": UNIVERSITY_ID, "term_key": "2026/2027-1",
            "course_code": "SHARED", "kind": "ADD_SECTION", "seats": 30}
    try:
        with TestClient(app) as client:
            response = client.post("/api/v1/institutional/analytics/simulate", json=body)
            assert response.status_code == 200
            assert response.json()["simulation_only"] is True
            assert response.json()["capacity_after"] == 35
            assert client.post("/api/v1/institutional/analytics/simulate",
                               json={**body, "sql": "select * from students"}).status_code == 422
    finally:
        app.dependency_overrides.clear()
