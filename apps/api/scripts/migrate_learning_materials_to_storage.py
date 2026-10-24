"""Verify and copy governed learning materials to Supabase Private Storage.

Dry-run is the default. Hosted execution requires both ``--apply`` and
``--allow-hosted`` so this command cannot accidentally mutate production during
ordinary validation. Metadata is switched one row at a time only after the
uploaded object is downloaded through the service role and its SHA-256 matches.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import sys
from urllib.parse import quote, urlsplit

import httpx


BUCKET = "learning-materials"
ROOT = Path(__file__).resolve().parents[1] / "private" / "learning-materials"
EXPECTED_FILE_SIZE_LIMIT = 50 * 1024 * 1024
EXPECTED_MIME_TYPES = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
})


def _headers(key: str, *, prefer: str | None = None) -> dict[str, str]:
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_local(url: str) -> bool:
    parsed = urlsplit(url)
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}


def _validate_bucket(bucket: object) -> None:
    if not isinstance(bucket, dict) or bucket.get("public") is not False:
        raise RuntimeError("learning-materials bucket is not private")
    if bucket.get("file_size_limit") != EXPECTED_FILE_SIZE_LIMIT:
        raise RuntimeError("learning-materials bucket has an unexpected file-size limit")
    allowed = bucket.get("allowed_mime_types")
    if not isinstance(allowed, list) or not EXPECTED_MIME_TYPES.issubset(allowed):
        raise RuntimeError("learning-materials bucket has unexpected MIME restrictions")


def _verify_object(payload: bytes, row: dict, *, label: str) -> None:
    if len(payload) != row["byte_size"] or _digest(payload) != row["sha256"]:
        raise RuntimeError(f"{label} size/hash mismatch for {row['id']}")


def migrate(url: str, key: str, *, apply: bool, allow_hosted: bool) -> int:
    url = url.rstrip("/")
    if not _is_local(url) and not allow_hosted:
        raise RuntimeError("refusing hosted Supabase; pass --allow-hosted after release approval")
    with httpx.Client(timeout=120, follow_redirects=False) as client:
        bucket = client.get(f"{url}/storage/v1/bucket/{BUCKET}", headers=_headers(key))
        bucket.raise_for_status()
        _validate_bucket(bucket.json())

        response = client.get(
            f"{url}/rest/v1/learning_materials",
            headers=_headers(key),
            params={
                "select": "id,object_key,mime_type,byte_size,sha256,storage_provider,storage_bucket",
                "order": "object_key.asc",
            },
        )
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or not rows:
            raise RuntimeError("no learning-material metadata was returned")

        verified = 0
        migrated = 0
        already_migrated = 0
        for row in rows:
            if not isinstance(row, dict):
                raise RuntimeError("learning-material metadata contains a non-object row")
            candidate = (ROOT / row["object_key"]).resolve()
            try:
                candidate.relative_to(ROOT.resolve())
            except ValueError as error:
                raise RuntimeError(f"unsafe object path for {row['id']}") from error
            payload = candidate.read_bytes()
            _verify_object(payload, row, label="local")
            verified += 1
            if not apply:
                continue

            object_path = quote(row["object_key"], safe="/")
            provider = row.get("storage_provider")
            storage_bucket = row.get("storage_bucket")
            if provider == "supabase_private":
                if storage_bucket != BUCKET:
                    raise RuntimeError(f"unexpected private bucket for {row['id']}")
                stored = client.get(
                    f"{url}/storage/v1/object/authenticated/{BUCKET}/{object_path}",
                    headers=_headers(key),
                )
                stored.raise_for_status()
                _verify_object(stored.content, row, label="private object")
                already_migrated += 1
                continue
            if provider != "local_private" or storage_bucket is not None:
                raise RuntimeError(f"unsupported storage state for {row['id']}")

            upload = client.post(
                f"{url}/storage/v1/object/{BUCKET}/{object_path}",
                headers={
                    **_headers(key),
                    "Content-Type": row["mime_type"],
                    "x-upsert": "true",
                },
                content=payload,
            )
            upload.raise_for_status()
            stored = client.get(
                f"{url}/storage/v1/object/authenticated/{BUCKET}/{object_path}",
                headers=_headers(key),
            )
            stored.raise_for_status()
            _verify_object(stored.content, row, label="private object")

            update = client.patch(
                f"{url}/rest/v1/learning_materials",
                headers=_headers(key, prefer="return=representation"),
                params={
                    "id": f"eq.{row['id']}",
                    "storage_provider": "eq.local_private",
                    "sha256": f"eq.{row['sha256']}",
                    "byte_size": f"eq.{row['byte_size']}",
                    "object_key": f"eq.{row['object_key']}",
                },
                json={"storage_provider": "supabase_private", "storage_bucket": BUCKET},
            )
            update.raise_for_status()
            updated = update.json()
            if not isinstance(updated, list) or len(updated) != 1 or updated[0].get("id") != row["id"]:
                raise RuntimeError(f"metadata switch lost a concurrency race for {row['id']}")
            migrated += 1

    mode = "applied" if apply else "dry-run"
    print(
        f"learning-material storage {mode}: verified={verified} "
        f"migrated={migrated} already_migrated={already_migrated}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="upload and switch verified rows")
    parser.add_argument(
        "--allow-hosted", action="store_true",
        help="permit a non-local URL; use only after explicit release authorization",
    )
    args = parser.parse_args()
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY", "")
    if not url or not key:
        parser.error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    try:
        return migrate(url, key, apply=args.apply, allow_hosted=args.allow_hosted)
    except (httpx.HTTPError, OSError, RuntimeError) as error:
        print(f"learning-material storage migration failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
