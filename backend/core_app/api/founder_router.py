"""Founder dashboard router — realtime operational metrics from live state."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings

from ..models import IntegrationState
from ..models.billing_queue import BillingQueueService
from ..services.aws_health_check import AWSHealthCheckService
from ..services.compliance_truth_engine import ComplianceTruthEngine

router = APIRouter(prefix="/api/v1/founder", tags=["founder"])
SQL_FUNC = cast(Any, func)
settings = get_settings()


def _require_founder(current_user: dict) -> None:
    """Raise HTTP 403 if the current user is not a founder."""
    if current_user.get("role") != "founder":
        raise HTTPException(status_code=403, detail="Founder access required")


def _serialize_datetime(dt: datetime | None) -> str | None:
    """Serialize a datetime (aware or naive) to ISO 8601 string, or None."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


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
    db: Session = Depends(db_session_dependency),
    current_user: dict = Depends(get_current_user),
) -> CashMetricsResponse:
    """Realtime cash metrics — Stripe settlements + internal ledger."""
    _require_founder(current_user)
    from ..models.billing_queue import BillingQueueItem

    now = datetime.now(UTC).replace(tzinfo=None)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)
    tenant_id = UUID(current_user.get("tenant_id"))

    # Collect from billing queue (paid items)
    collected_today = db.query(SQL_FUNC.sum(BillingQueueItem.cash_value)).filter(
        BillingQueueItem.created_at >= today_start,
        BillingQueueItem.tenant_id == tenant_id,
        BillingQueueItem.status == "resolved",
    ).scalar() or 0.0

    collected_week = db.query(SQL_FUNC.sum(BillingQueueItem.cash_value)).filter(
        BillingQueueItem.created_at >= week_start,
        BillingQueueItem.tenant_id == tenant_id,
        BillingQueueItem.status == "resolved",
    ).scalar() or 0.0

    collected_month = db.query(SQL_FUNC.sum(BillingQueueItem.cash_value)).filter(
        BillingQueueItem.created_at >= month_start,
        BillingQueueItem.tenant_id == tenant_id,
        BillingQueueItem.status == "resolved",
    ).scalar() or 0.0

    # Open A/R (not yet paid claims)
    open_ar = db.query(SQL_FUNC.sum(BillingQueueItem.cash_value)).filter(
        BillingQueueItem.tenant_id == tenant_id,
        BillingQueueItem.status == "pending",
    ).scalar() or 0.0

    # Failed renewals
    failed_renewals = db.query(BillingQueueItem.id).filter(
        BillingQueueItem.status == "failed",
        BillingQueueItem.created_at >= week_start,
        BillingQueueItem.tenant_id == tenant_id,
    ).count()

    return CashMetricsResponse(
        collected_today=float(collected_today),
        collected_week=float(collected_week),
        collected_month=float(collected_month),
        open_ar=float(open_ar),
        expected_30_days=float(collected_week * 4.3),
        failed_renewals_count=failed_renewals,
    )


@router.get("/billing")
async def founder_billing_metrics(
    db: Session = Depends(db_session_dependency),
    current_user: dict = Depends(get_current_user),
) -> BillingMetricsResponse:
    """Realtime billing queue metrics."""
    _require_founder(current_user)
    tenant_id = UUID(current_user.get("tenant_id"))
    service = BillingQueueService(db)

    now = datetime.now(UTC).replace(tzinfo=None)
    week_start = now - timedelta(days=7)

    stats = service.get_queue_statistics(tenant_id)

    from ..models.billing_queue import BillingQueueItem

    denials_week = db.query(BillingQueueItem.id).filter(
        BillingQueueItem.status == "denied",
        BillingQueueItem.created_at >= week_start,
        BillingQueueItem.tenant_id == tenant_id,
    ).count()

    missing_docs = db.query(BillingQueueItem.id).filter(
        BillingQueueItem.status == "pending",
        BillingQueueItem.tenant_id == tenant_id,
    ).count()

    aging_60_plus = db.query(BillingQueueItem.id).filter(
        BillingQueueItem.days_old >= 60,
        BillingQueueItem.tenant_id == tenant_id,
    ).count()

    return BillingMetricsResponse(
        queue_depth=stats["total_items"],
        highest_value_items_count=min(10, stats["total_items"]),
        denials_week=denials_week,
        missing_docs_count=missing_docs,
        aging_60_plus=aging_60_plus,
    )


@router.get("/compliance")
async def founder_compliance_metrics(
    db: Session = Depends(db_session_dependency),
    current_user: dict = Depends(get_current_user),
) -> ComplianceMetricsResponse:
    """Realtime NEMSIS/NERIS compliance status."""
    _require_founder(current_user)
    engine = ComplianceTruthEngine(db)
    status = engine.get_system_status()

    blocker_list = engine.list_blockers()
    critical_blockers = len([b for b in blocker_list if b.get("severity") in ("critical", "CRITICAL")])
    high_blockers = len([b for b in blocker_list if b.get("severity") in ("high", "HIGH")])

    export_statuses = engine.list_export_statuses()
    last_successful = max(
        (e.get("submitted_at") for e in export_statuses if e.get("final_status") == "accepted"),
        default=None,
    )

    return ComplianceMetricsResponse(
        nemsis_readiness=str(status.get("nemsis_overall_status", "unknown")),
        neris_readiness=str(status.get("neris_overall_status", "unknown")),
        charts_export_ready=len([e for e in export_statuses if e.get("export_status") == "ready"]),
        charts_blocked=len([e for e in export_statuses if e.get("export_status") == "blocked"]),
        blockers_critical=critical_blockers,
        blockers_high=high_blockers,
        last_export_success_at=last_successful,
    )


@router.get("/blockers")
async def founder_blockers(
    db: Session = Depends(db_session_dependency),
    current_user: dict = Depends(get_current_user),
):
    """Active blocker list with remediation hints."""
    _require_founder(current_user)
    engine = ComplianceTruthEngine(db)
    blockers = engine.list_blockers()

    critical = [b for b in blockers if b.get("severity") in ("critical", "CRITICAL")]
    high = [b for b in blockers if b.get("severity") in ("high", "HIGH")]

    return {
        "total_blockers": len(blockers),
        "critical_count": len(critical),
        "high_count": len(high),
        "critical_blockers": critical,
        "high_blockers": high,
    }


@router.get("/communications")
async def founder_comms_metrics(
    db: Session = Depends(db_session_dependency),
    current_user: dict = Depends(get_current_user),
):
    """Communications activity metrics."""
    _require_founder(current_user)

    def _integration_healthy(vendor: str) -> bool:
        state = db.query(IntegrationState).filter(IntegrationState.vendor == vendor).first()
        return bool(state and state.is_healthy)

    return {
        "telemetry_status": "unavailable",
        "reason": "Founder communications aggregates are not currently emitted by backend services.",
        "unread_emails": None,
        "active_sms_threads": None,
        "missed_calls": None,
        "fax_failures_today": None,
        "mail_in_production": None,
        "integration_health": {
            "telnyx": "healthy" if _integration_healthy("telnyx") else "unhealthy",
            "lob": "healthy" if _integration_healthy("lob") else "unhealthy",
        },
    }


@router.get("/system")
async def founder_system_health(
    db: Session = Depends(db_session_dependency),
    current_user: dict = Depends(get_current_user),
) -> SystemHealthResponse:
    """System health status."""
    _require_founder(current_user)

    health = AWSHealthCheckService(db)
    db_check = health.check_database()
    redis_check = health.check_redis()
    stripe_check = health.check_stripe()

    def _integration_healthy(vendor: str) -> bool:
        state = db.query(IntegrationState).filter(IntegrationState.vendor == vendor).first()
        return bool(state and state.is_healthy)

    checks = {
        "database": db_check.get("status") == "healthy",
        "redis": redis_check.get("status") == "healthy",
        "stripe": stripe_check.get("status") == "healthy",
        "telnyx": _integration_healthy("telnyx"),
        "lob": _integration_healthy("lob"),
        "cad": bool(settings.enable_cad_integration),
    }
    deployment_readiness_score = round(
        sum(1 for ok in checks.values() if ok) / max(len(checks), 1),
        2,
    )

    return SystemHealthResponse(
        database_healthy=checks["database"],
        redis_healthy=checks["redis"],
        stripe_healthy=checks["stripe"],
        telnyx_healthy=checks["telnyx"],
        lob_healthy=checks["lob"],
        cadintegration_healthy=checks["cad"],
        deployment_readiness_score=deployment_readiness_score,
    )


@router.get("/deployment")
async def founder_deployment_readiness(
    db: Session = Depends(db_session_dependency),
    current_user: dict = Depends(get_current_user),
):
    """Deployment readiness status."""
    _require_founder(current_user)
    health = AWSHealthCheckService(db)

    db_check = health.check_database()
    redis_check = health.check_redis()
    stripe_check = health.check_stripe()
    s3_check = health.check_s3()
    sqs_check = health.check_sqs()
    secrets_check = health.check_secrets_manager()

    readiness_checks = {
        "database": db_check.get("status"),
        "redis": redis_check.get("status"),
        "stripe": stripe_check.get("status"),
        "s3": s3_check.get("status"),
        "sqs": sqs_check.get("status"),
        "secrets": secrets_check.get("status"),
    }
    healthy_count = sum(1 for status in readiness_checks.values() if status == "healthy")
    completion_percent = round((healthy_count / max(len(readiness_checks), 1)) * 100)
    deployment_ready = healthy_count >= 5

    services_ok = all(status == "healthy" for status in readiness_checks.values())

    return {
        "phase": "runtime_readiness",
        "completion_percent": completion_percent,
        "migrations_status": "unverified_by_endpoint",
        "services_status": "all_healthy" if services_ok else "degraded",
        "workers_status": "unverified_by_endpoint",
        "deployment_ready_for_aws": deployment_ready,
        "go_live_target": "undetermined",
        "checks": readiness_checks,
    }



