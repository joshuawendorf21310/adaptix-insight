"""Scorecard API endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.schemas import ScorecardResponse
from core_app.services.scorecard_service import scorecard_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/insight/scorecard", tags=["Scorecards"])


@router.get("/executive", response_model=ScorecardResponse)
async def get_executive_scorecard(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get executive scorecard.

    Features implemented:
    - Executive scorecard API (Feature #60)
    """
    try:
        return await scorecard_service.get_executive_scorecard(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("executive_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/operational", response_model=ScorecardResponse)
async def get_operational_scorecard(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get operational scorecard.

    Features implemented:
    - Operational scorecard API (Feature #61)
    """
    try:
        return await scorecard_service.get_operational_scorecard(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("operational_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/billing", response_model=ScorecardResponse)
async def get_billing_scorecard(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get billing scorecard.

    Features implemented:
    - Billing scorecard API (Feature #68)
    """
    try:
        return await scorecard_service.get_billing_scorecard(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("billing_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/investor", response_model=ScorecardResponse)
async def get_investor_scorecard(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get investor scorecard.

    Features implemented:
    - Investor scorecard API (Feature #69)
    """
    try:
        return await scorecard_service.get_investor_scorecard(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("investor_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
