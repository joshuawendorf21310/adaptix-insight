"""Tests for scorecard service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models import KPIValue
from core_app.schemas import AggregationLevelEnum, KPIStatus
from core_app.services.kpi_service import kpi_service
from core_app.services.scorecard_service import scorecard_service


@pytest.mark.asyncio
async def test_executive_scorecard(db_session: AsyncSession):
    """
    Test executive scorecard generation.

    Features tested:
    - Executive scorecard API (Feature #60)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Seed KPI definitions
    await kpi_service.seed_kpi_definitions(db_session)

    # Create KPI values for executive metrics
    executive_kpis = [
        ("response_time", 8.5),
        ("chart_completion", 92.0),
        ("billing_throughput", 3.2),
        ("denial_rate", 8.0),
        ("staffing_coverage", 95.0),
        ("roi_realization", 215.0),
    ]

    for kpi_code, value in executive_kpis:
        await kpi_service.store_kpi_value(
            db=db_session,
            tenant_id=tenant_id,
            kpi_code=kpi_code,
            aggregation_level=AggregationLevelEnum.MONTHLY,
            period_start=now,
            period_end=period_end,
            value=value,
            status=KPIStatus.HEALTHY,
        )

    # Generate scorecard
    scorecard = await scorecard_service.get_executive_scorecard(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    assert scorecard.scorecard_type == "executive"
    assert scorecard.tenant_id == tenant_id
    assert len(scorecard.metrics) == 6
    assert all(m.metric_code in [kpi[0] for kpi in executive_kpis] for m in scorecard.metrics)


@pytest.mark.asyncio
async def test_operational_scorecard(db_session: AsyncSession):
    """
    Test operational scorecard generation.

    Features tested:
    - Operational scorecard API (Feature #61)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=1)

    # Seed KPI definitions
    await kpi_service.seed_kpi_definitions(db_session)

    # Create KPI values for operational metrics
    operational_kpis = [
        ("response_time", 7.8),
        ("turnout_time", 1.8),
        ("scene_time", 18.5),
        ("transport_time", 12.3),
        ("unit_utilization", 65.0),
    ]

    for kpi_code, value in operational_kpis:
        await kpi_service.store_kpi_value(
            db=db_session,
            tenant_id=tenant_id,
            kpi_code=kpi_code,
            aggregation_level=AggregationLevelEnum.DAILY,
            period_start=now,
            period_end=period_end,
            value=value,
            status=KPIStatus.HEALTHY,
        )

    # Generate scorecard
    scorecard = await scorecard_service.get_operational_scorecard(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    assert scorecard.scorecard_type == "operational"
    assert len(scorecard.metrics) >= 5


@pytest.mark.asyncio
async def test_billing_scorecard(db_session: AsyncSession):
    """
    Test billing scorecard generation.

    Features tested:
    - Billing scorecard API (Feature #68)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=7)

    # Seed KPI definitions
    await kpi_service.seed_kpi_definitions(db_session)

    # Create KPI values for billing metrics
    billing_kpis = [
        ("billing_throughput", 2.8),
        ("denial_rate", 6.5),
        ("chart_completion", 94.5),
        ("nemsis_readiness", 97.0),
    ]

    for kpi_code, value in billing_kpis:
        await kpi_service.store_kpi_value(
            db=db_session,
            tenant_id=tenant_id,
            kpi_code=kpi_code,
            aggregation_level=AggregationLevelEnum.WEEKLY,
            period_start=now,
            period_end=period_end,
            value=value,
            status=KPIStatus.HEALTHY,
        )

    # Generate scorecard
    scorecard = await scorecard_service.get_billing_scorecard(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    assert scorecard.scorecard_type == "billing"
    assert len(scorecard.metrics) == 4


@pytest.mark.asyncio
async def test_scorecard_metric_structure(db_session: AsyncSession):
    """
    Test scorecard metric structure and completeness.

    Features tested:
    - Scorecard metric assembly
    - Status and trend propagation
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Seed KPI definitions
    await kpi_service.seed_kpi_definitions(db_session)

    # Create a KPI value with full metadata
    await kpi_service.store_kpi_value(
        db=db_session,
        tenant_id=tenant_id,
        kpi_code="response_time",
        aggregation_level=AggregationLevelEnum.MONTHLY,
        period_start=now,
        period_end=period_end,
        value=8.5,
        status=KPIStatus.HEALTHY,
        delta_from_previous=-0.3,
        delta_from_target=0.5,
    )

    # Generate scorecard
    scorecard = await scorecard_service.get_executive_scorecard(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    # Find response_time metric
    response_time_metric = next((m for m in scorecard.metrics if m.metric_code == "response_time"), None)
    assert response_time_metric is not None
    assert response_time_metric.value == 8.5
    assert response_time_metric.status == KPIStatus.HEALTHY
    assert response_time_metric.delta_from_previous == -0.3
    assert response_time_metric.delta_from_target == 0.5
