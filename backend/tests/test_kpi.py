"""Tests for KPI service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models import KPIDefinition, KPIValue
from core_app.schemas import AggregationLevelEnum, KPIStatus, TrendDirection
from core_app.services.kpi_service import kpi_service


@pytest.mark.asyncio
async def test_kpi_status_classification(db_session: AsyncSession):
    """
    Test KPI status classification logic.

    Features tested:
    - KPI status classification (Feature #37)
    """
    # Test healthy status
    status = await kpi_service.calculate_kpi_status(
        value=5.0,
        threshold_warning=10.0,
        threshold_critical=15.0,
    )
    assert status == KPIStatus.HEALTHY

    # Test warning status
    status = await kpi_service.calculate_kpi_status(
        value=12.0,
        threshold_warning=10.0,
        threshold_critical=15.0,
    )
    assert status == KPIStatus.WARNING

    # Test critical status
    status = await kpi_service.calculate_kpi_status(
        value=20.0,
        threshold_warning=10.0,
        threshold_critical=15.0,
    )
    assert status == KPIStatus.CRITICAL


@pytest.mark.asyncio
async def test_trend_direction_classification(db_session: AsyncSession):
    """
    Test trend direction classification logic.

    Features tested:
    - KPI trend direction classification (Feature #40)
    """
    # Test upward trend
    trend = await kpi_service.calculate_trend_direction(
        current_value=110.0,
        previous_value=100.0,
        threshold=0.05,
    )
    assert trend == TrendDirection.UP

    # Test downward trend
    trend = await kpi_service.calculate_trend_direction(
        current_value=90.0,
        previous_value=100.0,
        threshold=0.05,
    )
    assert trend == TrendDirection.DOWN

    # Test stable (within threshold)
    trend = await kpi_service.calculate_trend_direction(
        current_value=102.0,
        previous_value=100.0,
        threshold=0.05,
    )
    assert trend == TrendDirection.STABLE

    # Test no previous value
    trend = await kpi_service.calculate_trend_direction(
        current_value=100.0,
        previous_value=None,
        threshold=0.05,
    )
    assert trend == TrendDirection.STABLE


@pytest.mark.asyncio
async def test_store_kpi_value(db_session: AsyncSession):
    """
    Test storing KPI values.

    Features tested:
    - KPI value storage with metadata
    - KPI target comparison (Feature #38)
    - KPI delta comparison (Feature #39)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()

    kpi_value = await kpi_service.store_kpi_value(
        db=db_session,
        tenant_id=tenant_id,
        kpi_code="response_time",
        aggregation_level=AggregationLevelEnum.DAILY,
        period_start=now,
        period_end=now + timedelta(days=1),
        value=8.5,
        status=KPIStatus.HEALTHY,
        trend_direction=TrendDirection.DOWN,
        delta_from_previous=-0.5,
        delta_from_target=0.5,
        quality_score=0.95,
    )

    assert kpi_value.tenant_id == tenant_id
    assert kpi_value.kpi_code == "response_time"
    assert kpi_value.value == 8.5
    assert kpi_value.status == KPIStatus.HEALTHY.value
    assert kpi_value.trend_direction == TrendDirection.DOWN.value
    assert kpi_value.delta_from_previous == -0.5
    assert kpi_value.delta_from_target == 0.5
    assert kpi_value.quality_score == 0.95


@pytest.mark.asyncio
async def test_get_kpi_values(db_session: AsyncSession):
    """
    Test retrieving KPI values with filtering.

    Features tested:
    - KPI value retrieval by tenant and time period
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()

    # Store multiple KPI values
    for i in range(3):
        await kpi_service.store_kpi_value(
            db=db_session,
            tenant_id=tenant_id,
            kpi_code=f"test_kpi_{i}",
            aggregation_level=AggregationLevelEnum.DAILY,
            period_start=now,
            period_end=now + timedelta(days=1),
            value=float(i * 10),
            status=KPIStatus.HEALTHY,
        )

    # Retrieve all KPIs
    kpis = await kpi_service.get_kpi_values(
        db=db_session,
        tenant_id=tenant_id,
        kpi_codes=None,
        aggregation_level=AggregationLevelEnum.DAILY,
        period_start=now,
        period_end=now + timedelta(days=1),
    )

    assert len(kpis) == 3

    # Retrieve specific KPI
    kpis = await kpi_service.get_kpi_values(
        db=db_session,
        tenant_id=tenant_id,
        kpi_codes=["test_kpi_1"],
        aggregation_level=AggregationLevelEnum.DAILY,
        period_start=now,
        period_end=now + timedelta(days=1),
    )

    assert len(kpis) == 1
    assert kpis[0].kpi_code == "test_kpi_1"
    assert kpis[0].value == 10.0


@pytest.mark.asyncio
async def test_kpi_definitions_seeded(db_session: AsyncSession):
    """
    Test that KPI definitions are properly seeded.

    Features tested:
    - KPI definition registry (Feature #31)
    - Core operational KPIs (Features #41-59)
    """
    await kpi_service.seed_kpi_definitions(db_session)

    # Verify response_time KPI exists
    kpi_def = await kpi_service.get_kpi_definition(db_session, "response_time")
    assert kpi_def is not None
    assert kpi_def.kpi_code == "response_time"
    assert kpi_def.kpi_name == "Response Time"
    assert kpi_def.formula_version == 1
    assert "cad" in kpi_def.source_domains or "epcr" in kpi_def.source_domains
    assert kpi_def.threshold_warning is not None
    assert kpi_def.threshold_critical is not None
    assert kpi_def.target_value is not None

    # Verify multiple KPIs seeded
    expected_kpis = [
        "response_time",
        "turnout_time",
        "scene_time",
        "transport_time",
        "chart_completion",
        "nemsis_readiness",
        "billing_throughput",
        "denial_rate",
        "staffing_coverage",
        "fatigue_risk",
        "unit_utilization",
        "ai_usage",
        "roi_realization",
    ]

    for kpi_code in expected_kpis:
        kpi_def = await kpi_service.get_kpi_definition(db_session, kpi_code)
        assert kpi_def is not None, f"KPI {kpi_code} should be seeded"
        assert kpi_def.is_active is True
