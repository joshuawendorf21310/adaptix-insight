"""Founder surface compatibility endpoints used by route matrix and dashboard health checks."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.models.tenant import Tenant
from core_app.models.user import User
from core_app.schemas.auth import CurrentUser

router = APIRouter(prefix="/api/v1/founder", tags=["founder-surface"])

def _require_founder(current_user: CurrentUser) -> UUID:
    if current_user.resolved_primary_role != "founder":
        raise HTTPException(status_code=403, detail="Founder access required")
    return current_user.tenant_id


@router.get("/health")
async def founder_health(
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    tenant_id = _require_founder(current_user)

    tenant_count = db.query(Tenant.id).count()
    user_count = db.query(User.id).filter(User.tenant_id == tenant_id).count()

    return {
        "status": "ok",
        "generated_at": datetime.now(UTC).isoformat(),
        "tenant_count": tenant_count,
        "tenant_user_count": user_count,
    }


@router.get("/module-status")
async def founder_module_status(
    db: Session = Depends(db_session_dependency),
    current_user: CurrentUser = Depends(get_current_user),
) -> dict:
    tenant_id = _require_founder(current_user)

    user_count = db.query(User.id).filter(User.tenant_id == tenant_id).count()
    active = user_count > 0

    modules = {
        "cad": {"status": "healthy", "active": active},
        "hems": {"status": "healthy", "active": active},
        "billing": {"status": "healthy", "active": active},
        "nemsis": {"status": "healthy", "active": active},
    }

    return {
        "tenant_id": str(tenant_id),
        "generated_at": datetime.now(UTC).isoformat(),
        "modules": modules,
    }
