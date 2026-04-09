from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core_app.api.dependencies import CurrentUser, get_current_user, require_role

router = APIRouter(prefix="/api/v1/system-health", tags=["System Health + Self-Healing"])


class HealthAlertRequest(BaseModel):
    service: str
    severity: str = "medium"
    message: str
    auto_resolve: bool = False


class SelfHealingRuleRequest(BaseModel):
    service: str
    trigger_metric: str
    threshold: float
    action: str
    cooldown_seconds: int = 300


class IncidentPostmortemRequest(BaseModel):
    incident_id: str
    root_cause: str
    timeline: list[dict] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    severity: str = "medium"


class RecoverySimRequest(BaseModel):
    service: str
    failure_scenario: str
    expected_rto_seconds: int = 300


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _metric_status(value: float | None, threshold: float) -> str:
    if value is None:
        return "unavailable"
    return "alert" if value >= threshold else "normal"


@router.get("/migrations/status")
async def migration_status(current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    return {"status": "not_connected", "applied_revisions": [], "current_revision": None, "as_of": _now_iso()}


@router.get("/realtime/status")
async def realtime_status(current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    return {"status": "not_connected", "publisher_mode": "standalone-shell", "redis_configured": False, "redis_connected": False, "redis_error": None, "as_of": _now_iso()}


@router.get("/dashboard")
async def health_dashboard(current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    return {"total_active_alerts": 0, "critical_alerts": 0, "services_monitored": ["ecs", "rds", "redis", "cloudfront", "api"], "overall_status": "not_connected", "as_of": _now_iso()}


@router.get("/services")
async def service_health(current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    return {"services": [{"service": "ecs", "status": "not_connected", "metric": "cpu_pct", "value": 0}, {"service": "rds", "status": "not_connected", "metric": "connections", "value": 0}], "as_of": _now_iso()}


@router.get("/integrations/readiness")
async def integration_readiness(current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    integrations = [{"name": "stripe", "status": "not_configured", "configured_count": 0, "required_count": 5, "missing_keys": ["all"]}, {"name": "lob", "status": "not_configured", "configured_count": 0, "required_count": 5, "missing_keys": ["all"]}, {"name": "telnyx", "status": "not_configured", "configured_count": 0, "required_count": 6, "missing_keys": ["all"]}]
    return {"integrations": integrations, "ready_count": 0, "total_count": len(integrations), "overall_status": "not_configured", "as_of": _now_iso()}


@router.get("/metrics/cpu")
async def cpu_metrics(current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    threshold = 80
    return {"metric": "cpu_utilization_pct", "value": 0, "threshold": threshold, "status": _metric_status(None, threshold), "as_of": _now_iso()}


@router.get("/metrics/memory")
async def memory_metrics(current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    threshold = 85
    return {"metric": "memory_utilization_pct", "value": 0, "threshold": threshold, "status": _metric_status(None, threshold), "as_of": _now_iso()}


@router.get("/metrics/api-latency")
async def api_latency(current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    threshold = 500
    return {"metric": "api_latency_ms_p99", "value": 0, "threshold": threshold, "status": _metric_status(None, threshold), "as_of": _now_iso()}


@router.get("/metrics/error-rate")
async def error_rate(current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    threshold = 2
    return {"metric": "error_rate_pct", "value": 0, "threshold": threshold, "status": _metric_status(None, threshold), "as_of": _now_iso()}


@router.post("/alerts")
async def create_alert(body: HealthAlertRequest, current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    return {"status": "queued-local-shell", "alert": body.model_dump(), "as_of": _now_iso()}


@router.post("/rules")
async def create_self_healing_rule(body: SelfHealingRuleRequest, current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    return {"status": "saved-local-shell", "rule": body.model_dump(), "as_of": _now_iso()}


@router.post("/postmortems")
async def create_postmortem(body: IncidentPostmortemRequest, current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    return {"status": "saved-local-shell", "postmortem": body.model_dump(), "as_of": _now_iso()}


@router.post("/recovery-simulations")
async def run_recovery_simulation(body: RecoverySimRequest, current: CurrentUser = Depends(get_current_user)):
    require_role(current, ["founder", "admin"])
    return {"status": "completed-local-shell", "simulation": body.model_dump(), "predicted_rto_seconds": body.expected_rto_seconds, "as_of": _now_iso()}
