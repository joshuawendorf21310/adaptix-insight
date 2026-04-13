"""Forecasting and predictive analytics API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.services.forecasting_service import forecasting_service

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/forecasting",
    tags=["Forecasting"],
)


@router.get("/input-preparation/{metric_name}")
async def prepare_forecasting_input(
    metric_name: str,
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Historical start date"),
    end_date: datetime = Query(..., description="Historical end date"),
    aggregation_interval: str = Query("daily", description="Aggregation interval (hourly/daily)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Prepare time-series data for forecasting.

    Feature #126: Forecasting input pipeline
    """
    try:
        result = await forecasting_service.prepare_forecasting_input(
            db=db,
            tenant_id=tenant_id,
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
            aggregation_interval=aggregation_interval,
        )
        return result
    except Exception as e:
        logger.error("forecasting_input_preparation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/call-volume")
async def forecast_call_volume(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Historical start date"),
    end_date: datetime = Query(..., description="Historical end date"),
    forecast_periods: int = Query(30, description="Number of periods to forecast"),
    db: AsyncSession = Depends(get_db),
):
    """
    Forecast future call/incident volume.

    Feature #127: Volume forecast support
    """
    try:
        result = await forecasting_service.forecast_call_volume(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            forecast_periods=forecast_periods,
        )
        return result
    except Exception as e:
        logger.error("call_volume_forecast_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/staffing-needs")
async def forecast_staffing_needs(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Historical start date"),
    end_date: datetime = Query(..., description="Historical end date"),
    forecast_periods: int = Query(30, description="Number of periods to forecast"),
    db: AsyncSession = Depends(get_db),
):
    """
    Forecast staffing requirements.

    Feature #128: Staffing forecast support
    """
    try:
        result = await forecasting_service.forecast_staffing_needs(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            forecast_periods=forecast_periods,
        )
        return result
    except Exception as e:
        logger.error("staffing_forecast_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transport-demand")
async def forecast_transport_demand(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Historical start date"),
    end_date: datetime = Query(..., description="Historical end date"),
    forecast_periods: int = Query(30, description="Number of periods to forecast"),
    db: AsyncSession = Depends(get_db),
):
    """
    Forecast transport demand patterns.

    Feature #129: Transport demand forecast
    """
    try:
        result = await forecasting_service.forecast_transport_demand(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            forecast_periods=forecast_periods,
        )
        return result
    except Exception as e:
        logger.error("transport_demand_forecast_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/denial-risk")
async def forecast_denial_risk(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Historical start date"),
    end_date: datetime = Query(..., description="Historical end date"),
    forecast_periods: int = Query(30, description="Number of periods to forecast"),
    db: AsyncSession = Depends(get_db),
):
    """
    Forecast billing denial risk.

    Feature #130: Denial-risk forecast
    """
    try:
        result = await forecasting_service.forecast_denial_risk(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            forecast_periods=forecast_periods,
        )
        return result
    except Exception as e:
        logger.error("denial_risk_forecast_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/budget-impact")
async def forecast_budget_impact(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Historical start date"),
    end_date: datetime = Query(..., description="Historical end date"),
    forecast_periods: int = Query(90, description="Number of periods to forecast"),
    db: AsyncSession = Depends(get_db),
):
    """
    Forecast budget and revenue impact.

    Feature #131: Budget-impact forecast
    """
    try:
        result = await forecasting_service.forecast_budget_impact(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            forecast_periods=forecast_periods,
        )
        return result
    except Exception as e:
        logger.error("budget_impact_forecast_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/unit-utilization")
async def forecast_unit_utilization(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Historical start date"),
    end_date: datetime = Query(..., description="Historical end date"),
    forecast_periods: int = Query(30, description="Number of periods to forecast"),
    db: AsyncSession = Depends(get_db),
):
    """
    Forecast unit/vehicle utilization rates.

    Feature #132: Utilization forecast
    """
    try:
        result = await forecasting_service.forecast_unit_utilization(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            forecast_periods=forecast_periods,
        )
        return result
    except Exception as e:
        logger.error("unit_utilization_forecast_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capacity-needs")
async def forecast_capacity_needs(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    start_date: datetime = Query(..., description="Historical start date"),
    end_date: datetime = Query(..., description="Historical end date"),
    forecast_periods: int = Query(30, description="Number of periods to forecast"),
    db: AsyncSession = Depends(get_db),
):
    """
    Forecast capacity and resource requirements.

    Feature #133: Capacity forecast
    """
    try:
        result = await forecasting_service.forecast_capacity_needs(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            forecast_periods=forecast_periods,
        )
        return result
    except Exception as e:
        logger.error("capacity_forecast_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
