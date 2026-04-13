"""Tests for forecasting service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models import AnalyticsEvent
from core_app.services.forecasting_service import forecasting_service


@pytest.mark.asyncio
async def test_forecasting_input_preparation(db_session: AsyncSession):
    """
    Test preparation of time-series data for forecasting.

    Features tested:
    - Forecasting input pipeline (Feature #126)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create daily events
    for i in range(30):
        event_date = start_date + timedelta(days=i)
        for j in range(5):  # 5 events per day
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=event_date + timedelta(hours=j),
                payload={"test": True},
            )
            db_session.add(event)
    await db_session.flush()

    # Prepare forecasting input
    result = await forecasting_service.prepare_forecasting_input(
        db=db_session,
        tenant_id=tenant_id,
        metric_name="test_metric",
        start_date=start_date,
        end_date=end_date,
        aggregation_interval="daily",
    )

    assert result["metric_name"] == "test_metric"
    assert result["data_points"] == 30
    assert len(result["time_series"]) == 30
    assert result["mean"] == 5.0
    assert result["trend"] in ["increasing", "decreasing", "stable"]


@pytest.mark.asyncio
async def test_call_volume_forecast(db_session: AsyncSession):
    """
    Test call volume forecasting.

    Features tested:
    - Volume forecast support (Feature #127)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=60)
    end_date = start_date + timedelta(days=60)

    # Create historical call events with growing pattern
    for i in range(60):
        event_date = start_date + timedelta(days=i)
        event_count = 10 + (i // 10)  # Gradually increasing
        for j in range(event_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=event_date + timedelta(hours=j % 24),
                payload={"call_id": f"call_{i}_{j}"},
            )
            db_session.add(event)
    await db_session.flush()

    # Generate forecast
    forecast = await forecasting_service.forecast_call_volume(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        forecast_periods=30,
    )

    assert forecast["metric_name"] == "call_volume"
    assert forecast["forecast_periods"] == 30
    assert len(forecast["forecast_values"]) == 30
    assert forecast["mean_forecast"] > 0
    assert forecast["model_type"] == "exponential_smoothing"


@pytest.mark.asyncio
async def test_staffing_needs_forecast(db_session: AsyncSession):
    """
    Test staffing needs forecasting.

    Features tested:
    - Staffing forecast support (Feature #128)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create events with varying crew assignments
    for i in range(30):
        event_date = start_date + timedelta(days=i)
        crew_count = 5 + (i % 3)  # Varies between 5-7 crews
        for j in range(crew_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=event_date + timedelta(hours=j),
                payload={"crew_id": f"crew_{j}"},
            )
            db_session.add(event)
    await db_session.flush()

    # Generate forecast
    forecast = await forecasting_service.forecast_staffing_needs(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        forecast_periods=14,
    )

    assert forecast["metric_name"] == "staffing_needs"
    assert forecast["forecast_periods"] == 14
    assert len(forecast["forecast_values"]) == 14
    assert forecast["recommended_min_staff"] > 0
    assert forecast["recommended_max_staff"] >= forecast["recommended_min_staff"]
    assert forecast["recommended_avg_staff"] > 0


@pytest.mark.asyncio
async def test_transport_demand_forecast(db_session: AsyncSession):
    """
    Test transport demand forecasting.

    Features tested:
    - Transport demand forecast (Feature #129)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=45)
    end_date = start_date + timedelta(days=45)

    # Create transport events
    for i in range(45):
        event_date = start_date + timedelta(days=i)
        transport_count = 8 + (i % 5)
        for j in range(transport_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="transport_complete",
                event_timestamp=event_date + timedelta(hours=j),
                payload={"transport_id": f"transport_{i}_{j}"},
            )
            db_session.add(event)
    await db_session.flush()

    # Generate forecast
    forecast = await forecasting_service.forecast_transport_demand(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        forecast_periods=21,
    )

    assert forecast["metric_name"] == "transport_demand"
    assert forecast["forecast_periods"] == 21
    assert len(forecast["forecast_values"]) == 21
    assert forecast["expected_daily_transports"] > 0
    assert forecast["peak_demand_day"] > 0


@pytest.mark.asyncio
async def test_denial_risk_forecast(db_session: AsyncSession):
    """
    Test billing denial risk forecasting.

    Features tested:
    - Denial-risk forecast (Feature #130)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=60)
    end_date = start_date + timedelta(days=60)

    # Create denial events with increasing trend
    for i in range(60):
        event_date = start_date + timedelta(days=i)
        denial_count = 2 + (i // 20)  # Gradually increasing denials
        for j in range(denial_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="billing",
                event_type="claim_denied",
                event_timestamp=event_date + timedelta(hours=j),
                payload={"claim_id": f"claim_{i}_{j}"},
            )
            db_session.add(event)
    await db_session.flush()

    # Generate forecast
    forecast = await forecasting_service.forecast_denial_risk(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        forecast_periods=30,
    )

    assert forecast["metric_name"] == "denial_risk"
    assert forecast["forecast_periods"] == 30
    assert len(forecast["forecast_values"]) == 30
    assert forecast["risk_level"] in ["low", "medium", "high"]
    assert forecast["expected_daily_denials"] >= 0


@pytest.mark.asyncio
async def test_budget_impact_forecast(db_session: AsyncSession):
    """
    Test budget and revenue impact forecasting.

    Features tested:
    - Budget-impact forecast (Feature #131)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=90)
    end_date = start_date + timedelta(days=90)

    # Create revenue events
    for i in range(90):
        event_date = start_date + timedelta(days=i)
        daily_revenue = 5000 + (i * 10)  # Growing revenue
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="billing",
            event_type="claim_paid",
            event_timestamp=event_date,
            payload={"amount": str(daily_revenue)},
        )
        db_session.add(event)
    await db_session.flush()

    # Generate forecast
    forecast = await forecasting_service.forecast_budget_impact(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        forecast_periods=90,
    )

    assert forecast["metric_name"] == "budget_impact"
    assert forecast["forecast_periods"] == 90
    assert len(forecast["forecast_values"]) == 90
    assert forecast["total_forecast_revenue"] > 0
    assert forecast["monthly_avg_revenue"] > 0


@pytest.mark.asyncio
async def test_unit_utilization_forecast(db_session: AsyncSession):
    """
    Test unit utilization forecasting.

    Features tested:
    - Utilization forecast (Feature #132)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create unit activity events
    for i in range(30):
        event_date = start_date + timedelta(days=i)
        unit_count = 10 + (i % 4)
        for j in range(unit_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="unit_dispatched",
                event_timestamp=event_date + timedelta(hours=j),
                payload={"unit_id": f"unit_{j}"},
            )
            db_session.add(event)
    await db_session.flush()

    # Generate forecast
    forecast = await forecasting_service.forecast_unit_utilization(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        forecast_periods=14,
    )

    assert forecast["metric_name"] == "unit_utilization"
    assert forecast["forecast_periods"] == 14
    assert len(forecast["forecast_values"]) == 14
    assert forecast["avg_daily_units_needed"] > 0
    assert forecast["peak_units_needed"] >= forecast["avg_daily_units_needed"]


@pytest.mark.asyncio
async def test_capacity_needs_forecast(db_session: AsyncSession):
    """
    Test capacity needs forecasting.

    Features tested:
    - Capacity forecast (Feature #133)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=60)
    end_date = start_date + timedelta(days=60)

    # Create capacity events
    for i in range(60):
        event_date = start_date + timedelta(days=i)
        event_count = 100 + (i * 2)  # Growing demand
        for j in range(event_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=event_date + timedelta(minutes=j),
                payload={"event_id": f"event_{i}_{j}"},
            )
            db_session.add(event)
    await db_session.flush()

    # Generate forecast
    forecast = await forecasting_service.forecast_capacity_needs(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        forecast_periods=30,
    )

    assert forecast["metric_name"] == "capacity_needs"
    assert forecast["forecast_periods"] == 30
    assert len(forecast["forecast_values"]) == 30
    assert forecast["recommended_avg_capacity"] > 0
    assert forecast["recommended_peak_capacity"] >= forecast["recommended_avg_capacity"]
    assert forecast["capacity_buffer_recommendation"] > forecast["recommended_peak_capacity"]


@pytest.mark.asyncio
async def test_confidence_bands(db_session: AsyncSession):
    """
    Test confidence band calculation.

    Features tested:
    - Confidence-band support (Feature #134)
    """
    # Create a sample forecast result
    forecast_result = {
        "metric_name": "test_metric",
        "forecast_values": [10.0, 12.0, 11.0, 13.0, 14.0],
        "forecast_periods": 5,
    }

    # Add confidence bands
    result = await forecasting_service.add_confidence_bands(
        forecast_result=forecast_result,
        confidence_level=0.95,
    )

    assert "confidence_bands" in result
    assert result["confidence_bands"]["confidence_level"] == 0.95
    assert len(result["confidence_bands"]["upper_band"]) == 5
    assert len(result["confidence_bands"]["lower_band"]) == 5
    assert result["confidence_bands"]["std_error"] > 0

    # Upper band should be >= forecast values
    for i in range(5):
        assert result["confidence_bands"]["upper_band"][i] >= result["forecast_values"][i]
        assert result["confidence_bands"]["lower_band"][i] <= result["forecast_values"][i]


@pytest.mark.asyncio
async def test_scenario_modeling(db_session: AsyncSession):
    """
    Test scenario modeling (best/worst/likely case).

    Features tested:
    - Best-case scenario modeling (Feature #135)
    - Worst-case scenario modeling (Feature #136)
    - Likely-case scenario modeling (Feature #137)
    """
    # Create a sample forecast result
    forecast_result = {
        "metric_name": "test_metric",
        "forecast_values": [100.0, 105.0, 110.0, 115.0, 120.0],
        "forecast_periods": 5,
    }

    # Add best case
    result = await forecasting_service.generate_best_case_scenario(
        forecast_result=forecast_result,
        improvement_factor=0.15,
    )
    assert "scenarios" in result
    assert "best_case" in result["scenarios"]
    assert len(result["scenarios"]["best_case"]["forecast_values"]) == 5
    assert result["scenarios"]["best_case"]["avg_value"] > 110.0

    # Add worst case
    result = await forecasting_service.generate_worst_case_scenario(
        forecast_result=result,
        deterioration_factor=0.15,
    )
    assert "worst_case" in result["scenarios"]
    assert len(result["scenarios"]["worst_case"]["forecast_values"]) == 5
    assert result["scenarios"]["worst_case"]["avg_value"] < 110.0

    # Add likely case
    result = await forecasting_service.generate_likely_case_scenario(forecast_result=result)
    assert "likely_case" in result["scenarios"]
    assert len(result["scenarios"]["likely_case"]["forecast_values"]) == 5

    # Verify relationships
    assert result["scenarios"]["best_case"]["avg_value"] > result["scenarios"]["likely_case"]["avg_value"]
    assert result["scenarios"]["likely_case"]["avg_value"] > result["scenarios"]["worst_case"]["avg_value"]
