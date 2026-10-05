"""Focused CORS policy tests for production and trusted preview frontends."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.cors import add_cors_middleware, allowed_origins


PRODUCTION_ORIGIN = "https://morshidi.vercel.app"
BRANCH_PREVIEW_ORIGIN = (
    "https://morshidi-git-fix-student-chat-recovery-"
    "mohannad-121s-projects.vercel.app"
)
GENERATED_PREVIEW_ORIGIN = (
    "https://morshidi-fdsa3o1cj-mohannad-121s-projects.vercel.app"
)
PREVIEW_ORIGINS = f"{BRANCH_PREVIEW_ORIGIN},{GENERATED_PREVIEW_ORIGIN}"


def cors_client() -> TestClient:
    application = FastAPI()
    add_cors_middleware(
        application,
        Settings(
            frontend_url=PRODUCTION_ORIGIN,
            cors_allowed_origins=PREVIEW_ORIGINS,
        ),
    )
    return TestClient(application)


def preflight(
    client: TestClient,
    path: str,
    origin: str,
    method: str = "POST",
    request_headers: str = "authorization,content-type",
):
    return client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": request_headers,
        },
    )


def assert_allowed(response, origin: str) -> None:
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


def test_production_frontend_origin_is_allowed() -> None:
    with cors_client() as client:
        response = preflight(client, "/api/v1/me/advisor", PRODUCTION_ORIGIN)
    assert_allowed(response, PRODUCTION_ORIGIN)


def test_branch_preview_origin_is_allowed() -> None:
    with cors_client() as client:
        response = preflight(client, "/api/v1/me/advisor", BRANCH_PREVIEW_ORIGIN)
    assert_allowed(response, BRANCH_PREVIEW_ORIGIN)


def test_generated_preview_origin_is_allowed() -> None:
    with cors_client() as client:
        response = preflight(client, "/api/v1/me/advisor", GENERATED_PREVIEW_ORIGIN)
    assert_allowed(response, GENERATED_PREVIEW_ORIGIN)


def test_random_vercel_project_origin_is_rejected() -> None:
    with cors_client() as client:
        response = preflight(
            client, "/api/v1/me/advisor", "https://evil-random-project.vercel.app"
        )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_malicious_arbitrary_origin_is_rejected() -> None:
    with cors_client() as client:
        response = preflight(client, "/api/v1/me/advisor", "https://attacker.example")
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_advisor_preflight_succeeds_for_preview() -> None:
    with cors_client() as client:
        response = preflight(client, "/api/v1/me/advisor", BRANCH_PREVIEW_ORIGIN)
    assert_allowed(response, BRANCH_PREVIEW_ORIGIN)
    assert "POST" in response.headers["access-control-allow-methods"]


def test_conversations_preflight_succeeds_for_preview() -> None:
    with cors_client() as client:
        response = preflight(
            client,
            "/api/v1/me/conversations?offset=0",
            BRANCH_PREVIEW_ORIGIN,
            method="GET",
        )
    assert_allowed(response, BRANCH_PREVIEW_ORIGIN)
    assert "GET" in response.headers["access-control-allow-methods"]


def test_authorization_and_content_type_headers_are_accepted() -> None:
    with cors_client() as client:
        response = preflight(client, "/api/v1/me/advisor", BRANCH_PREVIEW_ORIGIN)
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers


def test_unneeded_http_method_is_rejected() -> None:
    with cors_client() as client:
        response = preflight(
            client, "/api/v1/me/advisor", BRANCH_PREVIEW_ORIGIN, method="PUT"
        )
    assert response.status_code == 400
    assert "PUT" not in response.headers["access-control-allow-methods"]


def test_unneeded_request_header_is_rejected() -> None:
    with cors_client() as client:
        response = preflight(
            client,
            "/api/v1/me/advisor",
            BRANCH_PREVIEW_ORIGIN,
            request_headers="authorization,x-arbitrary-header",
        )
    assert response.status_code == 400
    assert "x-arbitrary-header" not in response.headers["access-control-allow-headers"]


def test_wildcard_origin_is_rejected_at_configuration_time() -> None:
    runtime_settings = Settings(
        frontend_url=PRODUCTION_ORIGIN,
        cors_allowed_origins="*",
    )
    with pytest.raises(ValueError, match="Invalid CORS origin"):
        allowed_origins(runtime_settings)
