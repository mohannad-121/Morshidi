"""Provision the governed private learning-material bucket through the Storage API.

Dry-run is the default. Hosted access requires ``--allow-hosted`` and creation
additionally requires ``--apply``. Existing buckets are accepted only when all
security settings exactly match the release contract.
"""

from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import urlsplit

import httpx


BUCKET = "learning-materials"
EXPECTED_FILE_SIZE_LIMIT = 50 * 1024 * 1024
EXPECTED_MIME_TYPES = frozenset({
    "application/pdf",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
})


def _headers(key: str) -> dict[str, str]:
    return {"apikey": key, "Authorization": f"Bearer {key}"}


def _is_local(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}


def _validate_bucket(bucket: object) -> None:
    if not isinstance(bucket, dict) or bucket.get("id") != BUCKET or bucket.get("name") != BUCKET:
        raise RuntimeError("learning-materials bucket identity is unexpected")
    if bucket.get("public") is not False:
        raise RuntimeError("learning-materials bucket is not private")
    if bucket.get("file_size_limit") != EXPECTED_FILE_SIZE_LIMIT:
        raise RuntimeError("learning-materials bucket has an unexpected file-size limit")
    allowed = bucket.get("allowed_mime_types")
    if not isinstance(allowed, list) or set(allowed) != EXPECTED_MIME_TYPES:
        raise RuntimeError("learning-materials bucket has unexpected MIME restrictions")


def _is_missing_bucket(response: httpx.Response) -> bool:
    if response.status_code == 404:
        return True
    if response.status_code != 400:
        return False
    try:
        payload = response.json()
    except ValueError:
        return False
    return isinstance(payload, dict) and payload.get("code") == "NoSuchBucket"


def provision(url: str, key: str, *, apply: bool, allow_hosted: bool) -> int:
    url = url.rstrip("/")
    if not _is_local(url) and not allow_hosted:
        raise RuntimeError("refusing hosted Supabase; pass --allow-hosted after release approval")

    endpoint = f"{url}/storage/v1/bucket/{BUCKET}"
    with httpx.Client(timeout=30, follow_redirects=False) as client:
        existing = client.get(endpoint, headers=_headers(key))
        if existing.status_code == 200:
            _validate_bucket(existing.json())
            print("learning-materials bucket: compatible existing bucket")
            return 0
        if not _is_missing_bucket(existing):
            existing.raise_for_status()
        if not apply:
            print("learning-materials bucket dry-run: creation required")
            return 0

        created = client.post(
            f"{url}/storage/v1/bucket",
            headers=_headers(key),
            json={
                "id": BUCKET,
                "name": BUCKET,
                "public": False,
                "file_size_limit": EXPECTED_FILE_SIZE_LIMIT,
                "allowed_mime_types": sorted(EXPECTED_MIME_TYPES),
            },
        )
        if created.status_code not in {200, 201, 409}:
            created.raise_for_status()

        verified = client.get(endpoint, headers=_headers(key))
        verified.raise_for_status()
        _validate_bucket(verified.json())
        print("learning-materials bucket: created and verified")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="create the bucket when absent")
    parser.add_argument(
        "--allow-hosted", action="store_true",
        help="permit a hosted URL; use only after explicit release authorization",
    )
    args = parser.parse_args()
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY", "")
    if not url or not key:
        parser.error("SUPABASE_URL and a server-only Supabase key are required")
    try:
        return provision(url, key, apply=args.apply, allow_hosted=args.allow_hosted)
    except (httpx.HTTPError, RuntimeError, ValueError) as error:
        print(f"learning-material bucket provisioning failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
