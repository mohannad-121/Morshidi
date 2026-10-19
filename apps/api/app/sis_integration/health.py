"""Deterministic health evaluator for university SIS integrations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from .adapter_interface import SISAdapter
from .models import HealthResult, UniversityIntegrationConfig


class IntegrationHealthEvaluator:
    """Evaluates real-time and operational health for a university SIS integration."""

    @staticmethod
    async def evaluate_health(
        adapter: SISAdapter | None,
        config: UniversityIntegrationConfig | None,
        *,
        last_sync_job: dict[str, Any] | None = None,
    ) -> HealthResult:
        """Probe SIS health and synthesize operational status."""
        if not config or not config.active:
            return HealthResult(
                status="NOT_CONFIGURED",
                connectivity=False,
                latency_ms=0.0,
                details={"reason": "Integration is not configured or disabled"},
            )

        if adapter is None:
            return HealthResult(
                status="NOT_CONFIGURED",
                connectivity=False,
                latency_ms=0.0,
                details={"reason": "No adapter available for provider"},
            )

        # 1. Live connectivity probe
        probe_result = await adapter.health_check()

        # 2. Correlate with recent sync operations
        details = dict(probe_result.details)
        status = probe_result.status

        if last_sync_job:
            job_status = last_sync_job.get("status")
            details["last_sync_status"] = job_status
            details["last_sync_started"] = last_sync_job.get("started_at")
            if job_status == "FAILED" and status == "HEALTHY":
                status = "DEGRADED"
                details["degradation_reason"] = "Last synchronization job failed"

        if probe_result.latency_ms > 2500.0 and status == "HEALTHY":
            status = "DEGRADED"
            details["degradation_reason"] = f"High latency ({probe_result.latency_ms}ms > 2500ms)"

        return HealthResult(
            status=status,
            connectivity=probe_result.connectivity,
            latency_ms=probe_result.latency_ms,
            details=details,
            checked_at=datetime.utcnow(),
        )

