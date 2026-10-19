"""Webhook ingestion engine with HMAC verification, replay protection, and event dispatch."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import time
from typing import Any
from uuid import UUID

from .errors import (
    WebhookReplayedError,
    WebhookSignatureInvalidError,
)
from .security import resolve_secret

MAX_WEBHOOK_AGE_SECONDS = 300  # 5-minute replay window
MAX_FUTURE_SKEW_SECONDS = 60   # 1-minute allowable clock skew


class WebhookEngine:
    """Verifies and processes inbound webhooks from external university SIS."""

    def __init__(self, processed_event_ids: set[str] | None = None) -> None:
        # In-memory deduplication set (in production backed by DB or Redis)
        self._processed_event_ids: set[str] = processed_event_ids if processed_event_ids is not None else set()

    @staticmethod
    def verify_hmac_signature(
        raw_body: bytes,
        signature_header: str | None,
        secret: str,
    ) -> bool:
        """Verify HMAC-SHA256 signature using constant-time comparison."""
        if not signature_header or not secret:
            return False

        # Support formats: "sha256=<hex>" or raw hex
        expected_sig = signature_header.strip()
        if expected_sig.startswith("sha256="):
            expected_sig = expected_sig.split("sha256=", 1)[1]

        computed_sig = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed_sig.lower(), expected_sig.lower())

    @staticmethod
    def verify_timestamp(timestamp_str: str | None) -> None:
        """Enforce strict replay window to prevent replay attacks."""
        if not timestamp_str or not timestamp_str.strip():
            raise WebhookReplayedError("Webhook request is missing required timestamp header")

        try:
            # Try unix timestamp float/int or ISO 8601 string
            cleaned = timestamp_str.strip()
            if cleaned.isdigit() or (cleaned.replace(".", "", 1).isdigit() and cleaned.count(".") == 1):
                event_ts = float(cleaned)
            else:
                # ISO format
                dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
                event_ts = dt.timestamp()
        except Exception as err:
            raise WebhookReplayedError(f"Malformed webhook timestamp: '{timestamp_str}'") from err

        now_ts = time.time()
        age = now_ts - event_ts

        if age > MAX_WEBHOOK_AGE_SECONDS:
            raise WebhookReplayedError(
                f"Webhook timestamp is stale ({int(age)}s old, exceeds {MAX_WEBHOOK_AGE_SECONDS}s limit)"
            )
        if age < -MAX_FUTURE_SKEW_SECONDS:
            raise WebhookReplayedError(
                f"Webhook timestamp is in the future by {int(-age)}s (exceeds allowable clock skew)"
            )

    def is_duplicate_event(self, event_id: str | None) -> bool:
        """Check if event has already been ingested."""
        if not event_id:
            return False
        return event_id in self._processed_event_ids

    def mark_event_processed(self, event_id: str | None) -> None:
        """Record event ID to prevent duplicate processing."""
        if event_id:
            self._processed_event_ids.add(event_id)

    def process_inbound_webhook(
        self,
        *,
        raw_body: bytes,
        headers: dict[str, str],
        webhook_secret: str,
        event_id: str | None = None,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Validate signature, timestamp, and idempotency, returning dispatch context."""
        # 1. Signature verification
        sig_header = (
            headers.get("x-morshidi-signature")
            or headers.get("x-hub-signature-256")
            or headers.get("x-signature-256")
        )
        if not self.verify_hmac_signature(raw_body, sig_header, webhook_secret):
            raise WebhookSignatureInvalidError("Inbound webhook signature verification failed")

        # 2. Timestamp replay defense
        ts_header = (
            timestamp
            or headers.get("x-morshidi-timestamp")
            or headers.get("x-timestamp")
        )
        self.verify_timestamp(ts_header)

        # 3. Idempotency deduplication
        evt_id = (
            event_id
            or headers.get("x-morshidi-event-id")
            or headers.get("x-event-id")
        )
        if evt_id and self.is_duplicate_event(evt_id):
            return {
                "status": "DUPLICATE",
                "event_id": evt_id,
                "message": "Event was previously ingested and processed",
            }

        if evt_id:
            self.mark_event_processed(evt_id)

        return {
            "status": "ACCEPTED",
            "event_id": evt_id,
            "timestamp": ts_header,
        }

