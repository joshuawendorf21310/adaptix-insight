"""Tests for executive insights service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models import AnalyticsEvent, KPIValue
from core_app.schemas import KPIStatus
from core_app.services.executive_insights_service import executive_insights_service


@pytest.mark.asyncio
async def test_executive_summary_generation(db_session: AsyncSession):
    """
    Test executive summary generation.

    Features tested:
    - Executive summary generation (Feature #138)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create events across multiple domains
    domains = ["cad", "epcr", "billing"]
    for domain in domains:
        for i in range(10):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain=domain,
                event_type=f"{domain}_event",
                event_timestamp=now + timedelta(days=i),
                payload={"test": True},
            )
            db_session.add(event)
    await db_session.flush()

    # Generate summary
    summary = await executive_insights_service.generate_executive_summary(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    assert summary["summary_type"] == "executive"
    assert summary["total_events"] == 30
    assert summary["active_domains"] == 3
    assert summary["top_domain"] in domains
    assert "domain_breakdown" in summary


@pytest.mark.asyncio
async def test_kpi_highlights_report(db_session: AsyncSession):
    """
    Test KPI highlights generation.

    Features tested:
    - KPI highlights report (Feature #139)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create KPI values with mixed statuses
    kpi_data = [
        ("response_time", 7.5, KPIStatus.HEALTHY, 1.0),
        ("chart_completion", 95.0, KPIStatus.HEALTHY, 5.0),
        ("denial_rate", 15.0, KPIStatus.WARNING, -3.0),
        ("unit_utilization", 85.0, KPIStatus.CRITICAL, -10.0),
    ]

    for kpi_code, value, status, delta in kpi_data:
        kpi = KPIValue(
            tenant_id=tenant_id,
            kpi_code=kpi_code,
            aggregation_level="monthly",
            period_start=now,
            period_end=period_end,
            value=value,
            status=status,
            delta_from_target=delta,
        )
        db_session.add(kpi)
    await db_session.flush()

    # Generate highlights
    highlights = await executive_insights_service.generate_kpi_highlights(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
        top_n=5,
    )

    assert highlights["report_type"] == "kpi_highlights"
    assert len(highlights["top_performers"]) >= 1
    assert len(highlights["underperformers"]) >= 1
    assert highlights["total_kpis_analyzed"] == 4


@pytest.mark.asyncio
async def test_trend_alert_generation(db_session: AsyncSession):
    """
    Test trend alert generation.

    Features tested:
    - Trend alert generation (Feature #140)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()

    # Create deteriorating trend
    for i in range(5):
        period_start = now - timedelta(days=(5 - i) * 30)
        period_end = period_start + timedelta(days=30)
        value = 100.0 - (i * 10)  # Declining values

        kpi = KPIValue(
            tenant_id=tenant_id,
            kpi_code="response_time",
            aggregation_level="monthly",
            period_start=period_start,
            period_end=period_end,
            value=value,
            status=KPIStatus.HEALTHY if i < 3 else KPIStatus.WARNING,
        )
        db_session.add(kpi)

    # Create improving trend
    for i in range(5):
        period_start = now - timedelta(days=(5 - i) * 30)
        period_end = period_start + timedelta(days=30)
        value = 50.0 + (i * 10)  # Improving values

        kpi = KPIValue(
            tenant_id=tenant_id,
            kpi_code="chart_completion",
            aggregation_level="monthly",
            period_start=period_start,
            period_end=period_end,
            value=value,
            status=KPIStatus.HEALTHY,
        )
        db_session.add(kpi)

    await db_session.flush()

    # Generate trend alerts
    alerts = await executive_insights_service.generate_trend_alerts(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now - timedelta(days=150),
        period_end=now,
    )

    assert alerts["alert_type"] == "trend_alerts"
    assert alerts["total_alerts"] >= 1
    assert any(a["trend"] == "deteriorating" for a in alerts["alerts"])
    assert any(a["trend"] == "improving" for a in alerts["alerts"])


@pytest.mark.asyncio
async def test_performance_recommendation_engine(db_session: AsyncSession):
    """
    Test performance recommendation generation.

    Features tested:
    - Performance recommendation engine (Feature #141)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create underperforming KPIs
    kpi_codes = ["response_time", "chart_completion", "denial_rate", "unit_utilization"]

    for kpi_code in kpi_codes:
        kpi = KPIValue(
            tenant_id=tenant_id,
            kpi_code=kpi_code,
            aggregation_level="monthly",
            period_start=now,
            period_end=period_end,
            value=50.0,
            status=KPIStatus.WARNING if kpi_code != "denial_rate" else KPIStatus.CRITICAL,
        )
        db_session.add(kpi)
    await db_session.flush()

    # Generate recommendations
    recommendations = await executive_insights_service.generate_performance_recommendations(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    assert recommendations["recommendation_type"] == "performance"
    assert recommendations["total_recommendations"] >= 4
    assert all("kpi_code" in r for r in recommendations["recommendations"])
    assert all("recommendation" in r for r in recommendations["recommendations"])
    assert all("priority" in r for r in recommendations["recommendations"])


@pytest.mark.asyncio
async def test_cost_optimization_insights(db_session: AsyncSession):
    """
    Test cost optimization insight generation.

    Features tested:
    - Cost-optimization insight generation (Feature #142)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create unit events with low utilization
    for i in range(10):
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="dispatch",
            event_timestamp=now + timedelta(days=i),
            payload={"unit_id": f"unit_{i}"},
        )
        db_session.add(event)

    # Create billing events with high denials
    for i in range(20):
        event_type = "claim_denied" if i % 2 == 0 else "claim_paid"
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="billing",
            event_type=event_type,
            event_timestamp=now + timedelta(days=i),
            payload={"claim_id": f"claim_{i}"},
        )
        db_session.add(event)

    await db_session.flush()

    # Generate insights
    insights = await executive_insights_service.generate_cost_optimization_insights(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    assert insights["insight_type"] == "cost_optimization"
    assert insights["total_insights"] >= 1
    assert any(i["category"] == "billing" for i in insights["insights"])


@pytest.mark.asyncio
async def test_quality_improvement_insights(db_session: AsyncSession):
    """
    Test quality improvement insight generation.

    Features tested:
    - Quality-improvement insight generation (Feature #143)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create chart events with low completion rate
    for i in range(100):
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="epcr",
                event_type="chart_created",
                event_timestamp=now + timedelta(hours=i),
                payload={"chart_id": f"chart_{i}"},
            )
        )

    # Only 70% completed
    for i in range(70):
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="epcr",
                event_type="chart_completed",
                event_timestamp=now + timedelta(hours=i, minutes=30),
                payload={"chart_id": f"chart_{i}"},
            )
        )

    # Only 60% signed
    for i in range(60):
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="epcr",
                event_type="chart_signed",
                event_timestamp=now + timedelta(hours=i, minutes=45),
                payload={"chart_id": f"chart_{i}"},
            )
        )

    await db_session.flush()

    # Generate insights
    insights = await executive_insights_service.generate_quality_improvement_insights(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    assert insights["insight_type"] == "quality_improvement"
    assert insights["total_insights"] >= 1
    assert any(i["category"] == "documentation" for i in insights["insights"])


@pytest.mark.asyncio
async def test_capacity_planning_insights(db_session: AsyncSession):
    """
    Test capacity planning insight generation.

    Features tested:
    - Capacity-planning insight generation (Feature #144)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=7)

    # Create events with peak hour pattern
    for day in range(7):
        for hour in range(24):
            # Create peak at hour 14 (2 PM)
            event_count = 20 if hour == 14 else 5

            for _ in range(event_count):
                event = AnalyticsEvent(
                    tenant_id=tenant_id,
                    source_domain="cad",
                    event_type="dispatch",
                    event_timestamp=now + timedelta(days=day, hours=hour),
                    payload={"test": True},
                )
                db_session.add(event)

    await db_session.flush()

    # Generate insights
    insights = await executive_insights_service.generate_capacity_planning_insights(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    assert insights["insight_type"] == "capacity_planning"
    assert insights["peak_hour"] == 14
    assert insights["peak_volume"] > insights["average_hourly"]


@pytest.mark.asyncio
async def test_risk_assessment_generation(db_session: AsyncSession):
    """
    Test risk assessment insight generation.

    Features tested:
    - Risk-assessment insight generation (Feature #145)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create critical KPIs
    critical_kpis = ["response_time", "denial_rate", "chart_completion"]

    for kpi_code in critical_kpis:
        kpi = KPIValue(
            tenant_id=tenant_id,
            kpi_code=kpi_code,
            aggregation_level="monthly",
            period_start=now,
            period_end=period_end,
            value=100.0,
            status=KPIStatus.CRITICAL,
            threshold_critical=50.0,
        )
        db_session.add(kpi)

    await db_session.flush()

    # Generate risk assessment
    assessment = await executive_insights_service.generate_risk_assessment(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    assert assessment["assessment_type"] == "risk"
    assert assessment["total_risks"] == 3
    assert assessment["overall_risk_level"] == "high"
    assert all(r["risk_level"] in ["high", "medium"] for r in assessment["risks"])


@pytest.mark.asyncio
async def test_top_action_items_report(db_session: AsyncSession):
    """
    Test top action items generation.

    Features tested:
    - Top action-item report (Feature #146)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create critical KPIs
    kpi = KPIValue(
        tenant_id=tenant_id,
        kpi_code="denial_rate",
        aggregation_level="monthly",
        period_start=now,
        period_end=period_end,
        value=100.0,
        status=KPIStatus.CRITICAL,
        threshold_critical=50.0,
    )
    db_session.add(kpi)
    await db_session.flush()

    # Generate action items
    actions = await executive_insights_service.generate_top_action_items(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
        limit=10,
    )

    assert actions["report_type"] == "action_items"
    assert actions["total_items"] >= 1
    assert all("priority" in a for a in actions["action_items"])
    assert all("urgency" in a for a in actions["action_items"])


@pytest.mark.asyncio
async def test_monthly_executive_brief(db_session: AsyncSession):
    """
    Test monthly executive brief generation.

    Features tested:
    - Monthly executive brief (Feature #147)
    """
    tenant_id = uuid.uuid4()
    month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Create sample data
    for i in range(10):
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="dispatch",
            event_timestamp=month + timedelta(days=i),
            payload={"test": True},
        )
        db_session.add(event)
    await db_session.flush()

    # Generate brief
    brief = await executive_insights_service.generate_monthly_executive_brief(
        db=db_session,
        tenant_id=tenant_id,
        month=month,
    )

    assert brief["brief_type"] == "monthly_executive"
    assert "summary" in brief
    assert "kpi_highlights" in brief
    assert "trend_alerts" in brief
    assert "top_actions" in brief


@pytest.mark.asyncio
async def test_quarterly_review_report(db_session: AsyncSession):
    """
    Test quarterly business review generation.

    Features tested:
    - Quarterly review report (Feature #148)
    """
    tenant_id = uuid.uuid4()
    year = 2024
    quarter = 1

    # Create sample data
    period_start = datetime(year, 1, 1)
    for i in range(30):
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="dispatch",
            event_timestamp=period_start + timedelta(days=i),
            payload={"test": True},
        )
        db_session.add(event)
    await db_session.flush()

    # Generate review
    review = await executive_insights_service.generate_quarterly_review(
        db=db_session,
        tenant_id=tenant_id,
        quarter=quarter,
        year=year,
    )

    assert review["review_type"] == "quarterly"
    assert review["quarter"] == "Q1 2024"
    assert "executive_summary" in review
    assert "cost_optimization" in review
    assert "quality_improvement" in review
    assert "capacity_planning" in review


@pytest.mark.asyncio
async def test_annual_report_generation(db_session: AsyncSession):
    """
    Test annual performance report generation.

    Features tested:
    - Annual report generation (Feature #149)
    """
    tenant_id = uuid.uuid4()
    year = 2024

    # Create sample data
    period_start = datetime(year, 1, 1)
    for i in range(100):
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="dispatch",
            event_timestamp=period_start + timedelta(days=i * 3),
            payload={"test": True},
        )
        db_session.add(event)
    await db_session.flush()

    # Generate annual report
    report = await executive_insights_service.generate_annual_report(
        db=db_session,
        tenant_id=tenant_id,
        year=year,
    )

    assert report["report_type"] == "annual"
    assert report["year"] == year
    assert "annual_summary" in report
    assert "year_highlights" in report
    assert "strategic_recommendations" in report


@pytest.mark.asyncio
async def test_custom_insights_generation(db_session: AsyncSession):
    """
    Test custom insights generation.

    Features tested:
    - Custom insights (Features #150-154)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create sample data
    for i in range(20):
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="dispatch",
            event_timestamp=now + timedelta(days=i),
            payload={"test": True},
        )
        db_session.add(event)
    await db_session.flush()

    # Generate custom insights
    focus_areas = ["cost", "quality", "capacity", "risk", "performance"]
    insights = await executive_insights_service.generate_custom_insights(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
        focus_areas=focus_areas,
    )

    assert insights["insight_type"] == "custom"
    assert insights["focus_areas"] == focus_areas
    assert "cost_optimization" in insights["insights"]
    assert "quality_improvement" in insights["insights"]
    assert "capacity_planning" in insights["insights"]
    assert "risk_assessment" in insights["insights"]
    assert "performance_recommendations" in insights["insights"]
