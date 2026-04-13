"""Executive insights and strategic recommendations API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.services.executive_insights_service import executive_insights_service

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/executive-insights",
    tags=["Executive Insights"],
)


@router.get("/summary")
async def executive_summary(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate high-level executive summary.

    Feature #138: Executive summary generation
    """
    try:
        result = await executive_insights_service.generate_executive_summary(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
        return result
    except Exception as e:
        logger.error("executive_summary_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kpi-highlights")
async def kpi_highlights(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    top_n: int = Query(5, description="Number of top performers/underperformers to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Highlight top performing and underperforming KPIs.

    Feature #139: KPI highlights report
    """
    try:
        result = await executive_insights_service.generate_kpi_highlights(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            top_n=top_n,
        )
        return result
    except Exception as e:
        logger.error("kpi_highlights_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend-alerts")
async def trend_alerts(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate alerts for significant trends.

    Feature #140: Trend alert generation
    """
    try:
        result = await executive_insights_service.generate_trend_alerts(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
        return result
    except Exception as e:
        logger.error("trend_alerts_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendations")
async def performance_recommendations(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate actionable performance recommendations.

    Feature #141: Performance recommendation engine
    """
    try:
        result = await executive_insights_service.generate_performance_recommendations(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
        return result
    except Exception as e:
        logger.error("recommendations_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost-optimization")
async def cost_optimization_insights(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate cost optimization insights.

    Feature #142: Cost-optimization insight generation
    """
    try:
        result = await executive_insights_service.generate_cost_optimization_insights(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
        return result
    except Exception as e:
        logger.error("cost_optimization_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality-improvement")
async def quality_improvement_insights(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate quality improvement insights.

    Feature #143: Quality-improvement insight generation
    """
    try:
        result = await executive_insights_service.generate_quality_improvement_insights(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
        return result
    except Exception as e:
        logger.error("quality_improvement_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capacity-planning")
async def capacity_planning_insights(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate capacity planning insights.

    Feature #144: Capacity-planning insight generation
    """
    try:
        result = await executive_insights_service.generate_capacity_planning_insights(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
        return result
    except Exception as e:
        logger.error("capacity_planning_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk-assessment")
async def risk_assessment(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate risk assessment insights.

    Feature #145: Risk-assessment insight generation
    """
    try:
        result = await executive_insights_service.generate_risk_assessment(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
        return result
    except Exception as e:
        logger.error("risk_assessment_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/action-items")
async def top_action_items(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    limit: int = Query(10, description="Maximum number of action items"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate prioritized action items.

    Feature #146: Top action-item report
    """
    try:
        result = await executive_insights_service.generate_top_action_items(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            limit=limit,
        )
        return result
    except Exception as e:
        logger.error("action_items_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monthly-brief")
async def monthly_executive_brief(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    month: datetime = Query(..., description="Month for the brief (YYYY-MM-01)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate comprehensive monthly executive brief.

    Feature #147: Monthly executive brief
    """
    try:
        result = await executive_insights_service.generate_monthly_executive_brief(
            db=db,
            tenant_id=tenant_id,
            month=month,
        )
        return result
    except Exception as e:
        logger.error("monthly_brief_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quarterly-review")
async def quarterly_review(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    quarter: int = Query(..., description="Quarter number (1-4)", ge=1, le=4),
    year: int = Query(..., description="Year"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate quarterly business review.

    Feature #148: Quarterly review report
    """
    try:
        result = await executive_insights_service.generate_quarterly_review(
            db=db,
            tenant_id=tenant_id,
            quarter=quarter,
            year=year,
        )
        return result
    except Exception as e:
        logger.error("quarterly_review_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/annual-report")
async def annual_report(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    year: int = Query(..., description="Year"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate annual performance report.

    Feature #149: Annual report generation
    """
    try:
        result = await executive_insights_service.generate_annual_report(
            db=db,
            tenant_id=tenant_id,
            year=year,
        )
        return result
    except Exception as e:
        logger.error("annual_report_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/custom-insights")
async def custom_insights(
    tenant_id: uuid.UUID = Query(..., description="Tenant ID"),
    period_start: datetime = Query(..., description="Period start date"),
    period_end: datetime = Query(..., description="Period end date"),
    focus_areas: List[str] = Query(..., description="Focus areas (cost, quality, capacity, risk, performance)"),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate custom insights based on focus areas.

    Features #150-154: Custom insights for specific focus areas
    """
    try:
        result = await executive_insights_service.generate_custom_insights(
            db=db,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            focus_areas=focus_areas,
        )
        return result
    except Exception as e:
        logger.error("custom_insights_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
