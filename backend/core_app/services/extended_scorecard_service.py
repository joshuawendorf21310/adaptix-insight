"""Additional scorecard implementations for comprehensive coverage."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.schemas import AggregationLevelEnum, ScorecardMetric, ScorecardResponse
from core_app.services.kpi_service import kpi_service

logger = get_logger(__name__)


async def get_agency_scorecard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    agency_id: str,
    period_start: datetime,
    period_end: datetime,
) -> ScorecardResponse:
    """
    Generate agency-level scorecard.

    Feature #62: Agency scorecard API
    """
    agency_kpis = [
        "response_time",
        "turnout_time",
        "unit_utilization",
        "staffing_coverage",
        "chart_completion",
        "billing_throughput",
    ]

    kpis = await kpi_service.get_kpi_values(
        db=db,
        tenant_id=tenant_id,
        kpi_codes=agency_kpis,
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
        scorecard_type="agency",
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
        summary={"agency_id": agency_id},
    )


async def get_station_scorecard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    station_id: str,
    period_start: datetime,
    period_end: datetime,
) -> ScorecardResponse:
    """
    Generate station-level scorecard.

    Feature #63: Station scorecard API
    """
    station_kpis = [
        "response_time",
        "turnout_time",
        "unit_utilization",
        "staffing_coverage",
        "apparatus_utilization",
    ]

    kpis = await kpi_service.get_kpi_values(
        db=db,
        tenant_id=tenant_id,
        kpi_codes=station_kpis,
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
        scorecard_type="station",
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
        summary={"station_id": station_id},
    )


async def get_crew_scorecard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    crew_id: str,
    period_start: datetime,
    period_end: datetime,
) -> ScorecardResponse:
    """
    Generate crew-level scorecard.

    Feature #64: Crew scorecard API
    """
    crew_kpis = [
        "chart_completion",
        "nemsis_readiness",
        "scene_time",
        "fatigue_risk",
    ]

    kpis = await kpi_service.get_kpi_values(
        db=db,
        tenant_id=tenant_id,
        kpi_codes=crew_kpis,
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
        scorecard_type="crew",
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
        summary={"crew_id": crew_id},
    )


async def get_unit_scorecard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    unit_id: str,
    period_start: datetime,
    period_end: datetime,
) -> ScorecardResponse:
    """
    Generate unit-level scorecard.

    Feature #65: Unit scorecard API
    """
    unit_kpis = [
        "unit_utilization",
        "response_time",
        "scene_time",
        "transport_time",
    ]

    kpis = await kpi_service.get_kpi_values(
        db=db,
        tenant_id=tenant_id,
        kpi_codes=unit_kpis,
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
        scorecard_type="unit",
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
        summary={"unit_id": unit_id},
    )


async def get_apparatus_scorecard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    apparatus_id: str,
    period_start: datetime,
    period_end: datetime,
) -> ScorecardResponse:
    """
    Generate apparatus-level scorecard.

    Feature #66: Apparatus scorecard API
    """
    apparatus_kpis = [
        "apparatus_utilization",
        "unit_utilization",
        "response_time",
        "maintenance_compliance",
    ]

    kpis = await kpi_service.get_kpi_values(
        db=db,
        tenant_id=tenant_id,
        kpi_codes=apparatus_kpis,
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
        scorecard_type="apparatus",
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
        summary={"apparatus_id": apparatus_id},
    )


async def get_service_line_scorecard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    service_line: str,
    period_start: datetime,
    period_end: datetime,
) -> ScorecardResponse:
    """
    Generate service-line scorecard.

    Feature #67: Service-line scorecard API
    """
    service_line_kpis = [
        "response_time",
        "chart_completion",
        "billing_throughput",
        "denial_rate",
        "patient_satisfaction",
    ]

    kpis = await kpi_service.get_kpi_values(
        db=db,
        tenant_id=tenant_id,
        kpi_codes=service_line_kpis,
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
        scorecard_type="service_line",
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
        summary={"service_line": service_line},
    )


async def get_product_adoption_scorecard(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    period_start: datetime,
    period_end: datetime,
) -> ScorecardResponse:
    """
    Generate product adoption scorecard.

    Feature #70: Product-adoption scorecard API
    """
    adoption_kpis = [
        "ai_usage",
        "ai_cost",
        "chart_completion",
        "nemsis_readiness",
        "roi_realization",
    ]

    kpis = await kpi_service.get_kpi_values(
        db=db,
        tenant_id=tenant_id,
        kpi_codes=adoption_kpis,
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
        scorecard_type="product_adoption",
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        metrics=metrics,
        summary={"adoption_tracking": True},
    )

