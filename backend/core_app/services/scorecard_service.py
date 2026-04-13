"""Scorecard assembly and management service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.schemas import (
    AggregationLevelEnum,
    KPIStatus,
    ScorecardMetric,
    ScorecardResponse,
    TrendDirection,
)
from core_app.services.kpi_service import kpi_service

logger = get_logger(__name__)


class ScorecardService:
    """Service for scorecard assembly and generation."""

    async def get_executive_scorecard(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> ScorecardResponse:
        """
        Generate executive scorecard.

        Feature #60: Executive scorecard API
        """
        # Define executive KPIs
        executive_kpis = [
            "response_time",
            "chart_completion",
            "billing_throughput",
            "denial_rate",
            "staffing_coverage",
            "roi_realization",
        ]

        kpis = await kpi_service.get_kpi_values(
            db=db,
            tenant_id=tenant_id,
            kpi_codes=executive_kpis,
            aggregation_level=AggregationLevelEnum.MONTHLY,
            period_start=period_start,
            period_end=period_end,
        )

        metrics = [
            ScorecardMetric(
                metric_code=kpi.kpi_code,
                metric_name=kpi.kpi_name or kpi.kpi_code,
                value=kpi.value,
                status=kpi.status,
                trend_direction=kpi.trend_direction,
                delta_from_previous=kpi.delta_from_previous,
                delta_from_target=kpi.delta_from_target,
            )
            for kpi in kpis
        ]

        return ScorecardResponse(
            scorecard_type="executive",
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
            summary={"total_metrics": len(metrics), "kpi_types": executive_kpis},
        )

    async def get_operational_scorecard(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> ScorecardResponse:
        """
        Generate operational scorecard.

        Feature #61: Operational scorecard API
        """
        operational_kpis = [
            "response_time",
            "turnout_time",
            "scene_time",
            "transport_time",
            "unit_utilization",
            "staffing_coverage",
            "fatigue_risk",
        ]

        kpis = await kpi_service.get_kpi_values(
            db=db,
            tenant_id=tenant_id,
            kpi_codes=operational_kpis,
            aggregation_level=AggregationLevelEnum.DAILY,
            period_start=period_start,
            period_end=period_end,
        )

        metrics = [
            ScorecardMetric(
                metric_code=kpi.kpi_code,
                metric_name=kpi.kpi_name or kpi.kpi_code,
                value=kpi.value,
                status=kpi.status,
                trend_direction=kpi.trend_direction,
                delta_from_previous=kpi.delta_from_previous,
                delta_from_target=kpi.delta_from_target,
            )
            for kpi in kpis
        ]

        return ScorecardResponse(
            scorecard_type="operational",
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
        )

    async def get_billing_scorecard(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> ScorecardResponse:
        """
        Generate billing scorecard.

        Feature #68: Billing scorecard API
        """
        billing_kpis = [
            "billing_throughput",
            "denial_rate",
            "chart_completion",
            "nemsis_readiness",
        ]

        kpis = await kpi_service.get_kpi_values(
            db=db,
            tenant_id=tenant_id,
            kpi_codes=billing_kpis,
            aggregation_level=AggregationLevelEnum.WEEKLY,
            period_start=period_start,
            period_end=period_end,
        )

        metrics = [
            ScorecardMetric(
                metric_code=kpi.kpi_code,
                metric_name=kpi.kpi_name or kpi.kpi_code,
                value=kpi.value,
                status=kpi.status,
                trend_direction=kpi.trend_direction,
                delta_from_previous=kpi.delta_from_previous,
                delta_from_target=kpi.delta_from_target,
            )
            for kpi in kpis
        ]

        return ScorecardResponse(
            scorecard_type="billing",
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
        )

    async def get_investor_scorecard(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> ScorecardResponse:
        """
        Generate investor scorecard.

        Feature #69: Investor scorecard API
        """
        investor_kpis = [
            "roi_realization",
            "billing_throughput",
            "denial_rate",
            "ai_usage",
        ]

        kpis = await kpi_service.get_kpi_values(
            db=db,
            tenant_id=tenant_id,
            kpi_codes=investor_kpis,
            aggregation_level=AggregationLevelEnum.QUARTERLY,
            period_start=period_start,
            period_end=period_end,
        )

        metrics = [
            ScorecardMetric(
                metric_code=kpi.kpi_code,
                metric_name=kpi.kpi_name or kpi.kpi_code,
                value=kpi.value,
                status=kpi.status,
                trend_direction=kpi.trend_direction,
                delta_from_previous=kpi.delta_from_previous,
                delta_from_target=kpi.delta_from_target,
            )
            for kpi in kpis
        ]

        return ScorecardResponse(
            scorecard_type="investor",
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            metrics=metrics,
        )


# Singleton instance
scorecard_service = ScorecardService()
