"""Advanced analytics API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.services.advanced_analytics_service import advanced_analytics_service

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/advanced-analytics",
    tags=["Advanced Analytics"],
)


@router.get("/cohort-analysis")
async def cohort_analysis(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    cohort_start: datetime = Query(..., description="Cohort period start"),
    cohort_end: datetime = Query(..., description="Cohort period end"),
    metric: str = Query("retention", description="Metric to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """
    Perform cohort analysis.

    Feature #116: Cohort analysis support
    """
    try:
        result = await advanced_analytics_service.cohort_analysis(
            db=db,
            tenant_id=tenant_id,
            cohort_start=cohort_start,
            cohort_end=cohort_end,
            metric=metric,
        )
        return result
    except Exception as e:
        logger.error("cohort_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retention-analysis")
async def retention_analysis(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Analysis start date"),
    end_date: datetime = Query(..., description="Analysis end date"),
    retention_period_days: int = Query(30, description="Retention period in days"),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze user retention rates.

    Feature #117: Retention analysis support
    """
    try:
        result = await advanced_analytics_service.retention_analysis(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            retention_period_days=retention_period_days,
        )
        return result
    except Exception as e:
        logger.error("retention_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversion-analysis")
async def conversion_analysis(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Analysis start date"),
    end_date: datetime = Query(..., description="Analysis end date"),
    conversion_event: str = Query(..., description="Target conversion event"),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze conversion funnel metrics.

    Feature #118: Conversion analysis support
    """
    try:
        result = await advanced_analytics_service.conversion_analysis(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            conversion_event=conversion_event,
        )
        return result
    except Exception as e:
        logger.error("conversion_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payer-lifecycle")
async def payer_lifecycle_analysis(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Analysis start date"),
    end_date: datetime = Query(..., description="Analysis end date"),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze payer lifecycle and relationships.

    Feature #119: Payer lifecycle analysis
    """
    try:
        result = await advanced_analytics_service.payer_lifecycle_analysis(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("payer_lifecycle_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recurring-patients")
async def recurring_patient_analysis(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Analysis start date"),
    end_date: datetime = Query(..., description="Analysis end date"),
    recurrence_threshold: int = Query(3, description="Minimum visits to classify as recurring"),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze recurring patient patterns.

    Feature #120: Recurring patient analysis
    """
    try:
        result = await advanced_analytics_service.recurring_patient_analysis(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            recurrence_threshold=recurrence_threshold,
        )
        return result
    except Exception as e:
        logger.error("recurring_patient_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/no-show-patterns")
async def no_show_pattern_analysis(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Analysis start date"),
    end_date: datetime = Query(..., description="Analysis end date"),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze no-show and missed appointment patterns.

    Features #121-122: Missed-appointment and no-show pattern analysis
    """
    try:
        result = await advanced_analytics_service.no_show_pattern_analysis(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("no_show_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document-completion-lag")
async def document_completion_lag_analysis(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Analysis start date"),
    end_date: datetime = Query(..., description="Analysis end date"),
    db: AsyncSession = Depends(get_db),
):
    """
    Analyze document completion, signature, and export lag times.

    Features #123-125: Document completion, chart-signature, export-readiness lag analysis
    """
    try:
        result = await advanced_analytics_service.document_completion_lag_analysis(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("document_lag_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
