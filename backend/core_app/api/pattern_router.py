"""Pattern detection and trend analysis API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.services.pattern_detection_service import pattern_detection_service

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/patterns",
    tags=["Pattern Detection"],
)


@router.get("/seasonal/{metric_name}")
async def detect_seasonal_patterns(
    metric_name: str,
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect seasonal patterns in a metric.

    Feature #88: Seasonal pattern detection
    """
    try:
        result = await pattern_detection_service.detect_seasonal_patterns(
            db=db,
            tenant_id=tenant_id,
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("seasonal_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/day-of-week/{metric_name}")
async def detect_day_of_week_patterns(
    metric_name: str,
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect day-of-week patterns.

    Feature #89: Day-of-week pattern detection
    """
    try:
        result = await pattern_detection_service.detect_day_of_week_patterns(
            db=db,
            tenant_id=tenant_id,
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("day_of_week_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hour-of-day/{metric_name}")
async def detect_hour_of_day_patterns(
    metric_name: str,
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect hour-of-day patterns.

    Feature #90: Hour-of-day pattern detection
    """
    try:
        result = await pattern_detection_service.detect_hour_of_day_patterns(
            db=db,
            tenant_id=tenant_id,
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("hour_of_day_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents")
async def detect_incident_type_patterns(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect incident type patterns.

    Feature #91: Incident-type pattern detection
    """
    try:
        result = await pattern_detection_service.detect_incident_type_patterns(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("incident_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interventions")
async def detect_intervention_patterns(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect intervention patterns.

    Feature #92: Intervention pattern detection
    """
    try:
        result = await pattern_detection_service.detect_intervention_patterns(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("intervention_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/medications")
async def detect_medication_patterns(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect medication administration patterns.

    Feature #93: Medication pattern detection
    """
    try:
        result = await pattern_detection_service.detect_medication_patterns(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("medication_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/destinations")
async def detect_destination_patterns(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect destination facility patterns.

    Feature #94: Destination pattern detection
    """
    try:
        result = await pattern_detection_service.detect_destination_patterns(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("destination_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staffing-trends")
async def detect_staffing_trends(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect staffing level trends.

    Feature #95: Staffing-trend detection
    """
    try:
        result = await pattern_detection_service.detect_staffing_trends(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("staffing_trend_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/geographic")
async def detect_geographic_patterns(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect geographic hotspot patterns.

    Feature #96: Geographic hotspot detection
    """
    try:
        result = await pattern_detection_service.detect_geographic_patterns(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("geographic_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/response-times")
async def detect_response_time_patterns(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect response time patterns.

    Feature #97: Response-time pattern detection
    """
    try:
        result = await pattern_detection_service.detect_response_time_patterns(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("response_time_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unit-utilization")
async def detect_unit_utilization_patterns(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect unit utilization patterns.

    Feature #98: Unit-utilization pattern detection
    """
    try:
        result = await pattern_detection_service.detect_unit_utilization_patterns(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("unit_utilization_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/billing-denials")
async def detect_billing_denial_patterns(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect billing denial patterns.

    Feature #99: Billing-denial pattern detection
    """
    try:
        result = await pattern_detection_service.detect_billing_denial_patterns(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("billing_denial_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crew-performance")
async def detect_crew_performance_patterns(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Detect crew performance patterns.

    Feature #100: Crew-performance pattern detection
    """
    try:
        result = await pattern_detection_service.detect_crew_performance_patterns(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
    except Exception as e:
        logger.error("crew_performance_pattern_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
