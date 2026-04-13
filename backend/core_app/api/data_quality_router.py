"""Data quality API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.schemas import DataQualityResponse
from core_app.services.data_quality_service import data_quality_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/insight/quality", tags=["Data Quality"])


@router.get("/check", response_model=DataQualityResponse)
async def check_data_quality(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db),
) -> DataQualityResponse:
    """
    Check data quality across all source domains.

    Features implemented:
    - Source freshness warnings (Feature #155)
    - Stale analytics warnings (Feature #156)
    - Incomplete-data warnings (Feature #157)
    - Metric quality score (Feature #159)
    - Data completeness score (Feature #161)
    """
    try:
        return await data_quality_service.check_data_quality(db, tenant_id)
    except Exception as e:
        logger.error("data_quality_check_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check data quality: {str(e)}",
        )
