"""Explicit browser-origin policy for authenticated API requests."""

from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings, settings


LOCAL_FRONTEND_ORIGIN = "http://127.0.0.1:3000"
ALLOWED_METHODS = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = ["Authorization", "Content-Type"]


def _normalize_origin(value: str) -> str:
    origin = value.strip().rstrip("/")
    parsed = urlsplit(origin)
    if (
        origin == "*"
        or parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Invalid CORS origin: {value!r}")
    return origin


def allowed_origins(runtime_settings: Settings = settings) -> list[str]:
    """Return a validated, de-duplicated explicit origin allowlist."""

    configured = [
        runtime_settings.frontend_url,
        LOCAL_FRONTEND_ORIGIN,
        *runtime_settings.cors_allowed_origins.split(","),
    ]
    origins: list[str] = []
    for value in configured:
        if not value.strip():
            continue
        origin = _normalize_origin(value)
        if origin not in origins:
            origins.append(origin)
    return origins


def add_cors_middleware(
    application: FastAPI,
    runtime_settings: Settings = settings,
) -> None:
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins(runtime_settings),
        allow_credentials=True,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
    )
