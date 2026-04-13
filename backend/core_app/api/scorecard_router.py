"""Scorecard API endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.schemas import ScorecardResponse
from core_app.services.extended_scorecard_service import (
    get_agency_scorecard,
    get_apparatus_scorecard,
    get_crew_scorecard,
    get_product_adoption_scorecard,
    get_service_line_scorecard,
    get_station_scorecard,
    get_unit_scorecard,
)
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


@router.get("/agency/{agency_id}", response_model=ScorecardResponse)
async def get_agency_scorecard_endpoint(
    agency_id: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get agency-level scorecard.

    Features implemented:
    - Agency scorecard API (Feature #62)
    """
    try:
        return await get_agency_scorecard(
            db=db,
            tenant_id=tenant_id,
            agency_id=agency_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("agency_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/station/{station_id}", response_model=ScorecardResponse)
async def get_station_scorecard_endpoint(
    station_id: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get station-level scorecard.

    Features implemented:
    - Station scorecard API (Feature #63)
    """
    try:
        return await get_station_scorecard(
            db=db,
            tenant_id=tenant_id,
            station_id=station_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("station_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/crew/{crew_id}", response_model=ScorecardResponse)
async def get_crew_scorecard_endpoint(
    crew_id: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get crew-level scorecard.

    Features implemented:
    - Crew scorecard API (Feature #64)
    """
    try:
        return await get_crew_scorecard(
            db=db,
            tenant_id=tenant_id,
            crew_id=crew_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("crew_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/unit/{unit_id}", response_model=ScorecardResponse)
async def get_unit_scorecard_endpoint(
    unit_id: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get unit-level scorecard.

    Features implemented:
    - Unit scorecard API (Feature #65)
    """
    try:
        return await get_unit_scorecard(
            db=db,
            tenant_id=tenant_id,
            unit_id=unit_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("unit_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/apparatus/{apparatus_id}", response_model=ScorecardResponse)
async def get_apparatus_scorecard_endpoint(
    apparatus_id: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get apparatus-level scorecard.

    Features implemented:
    - Apparatus scorecard API (Feature #66)
    """
    try:
        return await get_apparatus_scorecard(
            db=db,
            tenant_id=tenant_id,
            apparatus_id=apparatus_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("apparatus_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/service-line/{service_line}", response_model=ScorecardResponse)
async def get_service_line_scorecard_endpoint(
    service_line: str,
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get service-line scorecard.

    Features implemented:
    - Service-line scorecard API (Feature #67)
    """
    try:
        return await get_service_line_scorecard(
            db=db,
            tenant_id=tenant_id,
            service_line=service_line,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("service_line_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/product-adoption", response_model=ScorecardResponse)
async def get_product_adoption_scorecard_endpoint(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start"),
    period_end: datetime = Query(..., description="Period end"),
    db: AsyncSession = Depends(get_db),
) -> ScorecardResponse:
    """
    Get product adoption scorecard.

    Features implemented:
    - Product-adoption scorecard API (Feature #70)
    """
    try:
        return await get_product_adoption_scorecard(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
    except Exception as e:
        logger.error("product_adoption_scorecard_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

