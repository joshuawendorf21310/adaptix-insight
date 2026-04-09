"""Founder surface compatibility endpoints used by route matrix and dashboard health checks."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from core_app.api.dependencies import CurrentUser, get_current_user

router = APIRouter(prefix="/api/v1/founder", tags=["founder-surface"])

def _require_founder(current_user: CurrentUser) -> str:
    if current_user.resolved_primary_role != "founder":
        raise HTTPException(status_code=403, detail="Founder access required")
    return current_user.tenant_id


@router.get("/health")
async def founder_health(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    tenant_id = _require_founder(current_user)

    return {
        "status": "ok",
        "generated_at": datetime.now(UTC).isoformat(),
        "tenant_count": 0,
        "tenant_user_count": 0,
        "tenant_id": tenant_id,
        "mode": "standalone-shell",
    }


@router.get("/module-status")
async def founder_module_status(
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    tenant_id = _require_founder(current_user)

    modules = {
        "cad": {"status": "not_connected", "active": False},
        "hems": {"status": "not_connected", "active": False},
        "billing": {"status": "not_connected", "active": False},
        "nemsis": {"status": "not_connected", "active": False},
    }

    return {
        "tenant_id": str(tenant_id),
        "generated_at": datetime.now(UTC).isoformat(),
        "modules": modules,
    }
