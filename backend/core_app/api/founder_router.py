"""Standalone founder insight router with truthful zero-state responses."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core_app.api.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/founder", tags=["founder"])


def _require_founder(current_user: CurrentUser) -> None:
    if current_user.resolved_primary_role != "founder":
        raise HTTPException(status_code=403, detail="Founder access required")


class CashMetricsResponse(BaseModel):
    collected_today: float
    collected_week: float
    collected_month: float
    open_ar: float
    expected_30_days: float
    failed_renewals_count: int


class BillingMetricsResponse(BaseModel):
    queue_depth: int
    highest_value_items_count: int
    denials_week: int
    missing_docs_count: int
    aging_60_plus: int


class ComplianceMetricsResponse(BaseModel):
    nemsis_readiness: str
    neris_readiness: str
    charts_export_ready: int
    charts_blocked: int
    blockers_critical: int
    blockers_high: int
    last_export_success_at: str | None


class SystemHealthResponse(BaseModel):
    database_healthy: bool
    redis_healthy: bool
    stripe_healthy: bool
    telnyx_healthy: bool
    lob_healthy: bool
    cadintegration_healthy: bool
    deployment_readiness_score: float


@router.get("/cash")
async def founder_cash_metrics(
    current_user: CurrentUser = Depends(get_current_user),
) -> CashMetricsResponse:
    _require_founder(current_user)
    return CashMetricsResponse(collected_today=0.0, collected_week=0.0, collected_month=0.0, open_ar=0.0, expected_30_days=0.0, failed_renewals_count=0)


@router.get("/billing")
async def founder_billing_metrics(
    current_user: CurrentUser = Depends(get_current_user),
) -> BillingMetricsResponse:
    _require_founder(current_user)
    return BillingMetricsResponse(queue_depth=0, highest_value_items_count=0, denials_week=0, missing_docs_count=0, aging_60_plus=0)


@router.get("/compliance")
async def founder_compliance_metrics(
    current_user: CurrentUser = Depends(get_current_user),
) -> ComplianceMetricsResponse:
    _require_founder(current_user)
    return ComplianceMetricsResponse(nemsis_readiness="not_connected", neris_readiness="not_connected", charts_export_ready=0, charts_blocked=0, blockers_critical=0, blockers_high=0, last_export_success_at=None)


@router.get("/blockers")
async def founder_blockers(
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_founder(current_user)
    return {
        "total_blockers": 0,
        "critical_count": 0,
        "high_count": 0,
        "critical_blockers": [],
        "high_blockers": [],
        "mode": "standalone-shell",
    }


@router.get("/communications")
async def founder_comms_metrics(
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_founder(current_user)

    return {
        "telemetry_status": "unavailable",
        "reason": "Founder communications aggregates are not currently emitted by backend services.",
        "unread_emails": None,
        "active_sms_threads": None,
        "missed_calls": None,
        "fax_failures_today": None,
        "mail_in_production": None,
        "integration_health": {
            "telnyx": "not_connected",
            "lob": "not_connected",
        },
    }


@router.get("/system")
async def founder_system_health(
    current_user: CurrentUser = Depends(get_current_user),
) -> SystemHealthResponse:
    _require_founder(current_user)
    return SystemHealthResponse(database_healthy=False, redis_healthy=False, stripe_healthy=False, telnyx_healthy=False, lob_healthy=False, cadintegration_healthy=False, deployment_readiness_score=0.0)


@router.get("/deployment")
async def founder_deployment_readiness(
    current_user: CurrentUser = Depends(get_current_user),
):
    _require_founder(current_user)
    return {
        "phase": "runtime_readiness",
        "completion_percent": 0,
        "migrations_status": "not_connected",
        "services_status": "not_connected",
        "workers_status": "unverified_by_endpoint",
        "deployment_ready_for_aws": False,
        "go_live_target": "undetermined",
        "checks": {
            "database": "not_connected",
            "redis": "not_connected",
            "stripe": "not_connected",
            "s3": "not_connected",
            "sqs": "not_connected",
            "secrets": "not_connected",
        },
    }



