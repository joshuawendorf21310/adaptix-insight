"""KPI API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.schemas import KPIListRequest, KPIListResponse
from core_app.services.kpi_service import kpi_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/insight/kpi", tags=["KPI Management"])


@router.post("/values", response_model=KPIListResponse)
async def get_kpi_values(
    request: KPIListRequest,
    db: AsyncSession = Depends(get_db),
) -> KPIListResponse:
    """
    Get KPI values for a time period.

    Features implemented:
    - KPI definition registry (Feature #31)
    - KPI status classification (Feature #37)
    - KPI target comparison (Feature #38)
    - KPI delta comparison (Feature #39)
    - KPI trend direction classification (Feature #40)
    """
    try:
        kpis = await kpi_service.get_kpi_values(
            db=db,
            tenant_id=request.tenant_id,
            kpi_codes=request.kpi_codes,
            aggregation_level=request.aggregation_level,
            period_start=request.period_start,
            period_end=request.period_end,
        )

        return KPIListResponse(kpis=kpis, count=len(kpis))

    except Exception as e:
        logger.error("kpi_values_endpoint_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve KPI values: {str(e)}",
        )
