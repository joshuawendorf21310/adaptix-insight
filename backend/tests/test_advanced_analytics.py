"""Tests for advanced analytics service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models import AnalyticsEvent
from core_app.services.advanced_analytics_service import advanced_analytics_service


@pytest.mark.asyncio
async def test_cohort_analysis(db_session: AsyncSession):
    """
    Test cohort analysis functionality.

    Features tested:
    - Cohort analysis support (Feature #116)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(days=90)
    end_date = start_date + timedelta(days=90)

    # Create user events across multiple months
    user_ids = [f"user_{i}" for i in range(10)]

    for month_offset in range(3):
        cohort_start = start_date + timedelta(days=month_offset * 30)

        for user_idx, user_id in enumerate(user_ids):
            # Each user has events in their cohort month and subsequent months
            for event_offset in range(3 - month_offset):
                event_date = cohort_start + timedelta(days=event_offset * 30 + user_idx)
                event = AnalyticsEvent(
                    tenant_id=tenant_id,
                    source_domain="cad",
                    event_type="user_activity",
                    event_timestamp=event_date,
                    payload={"user_id": user_id},
                )
                db_session.add(event)

    await db_session.flush()

    # Run cohort analysis
    result = await advanced_analytics_service.cohort_analysis(
        db=db_session,
        tenant_id=tenant_id,
        cohort_start=start_date,
        cohort_end=end_date,
        metric="retention",
    )

    assert "cohort_matrix" in result
    assert result["total_cohorts"] > 0
    assert result["total_users"] == len(user_ids)
    assert "analysis_period" in result


@pytest.mark.asyncio
async def test_retention_analysis(db_session: AsyncSession):
    """
    Test user retention analysis.

    Features tested:
    - Retention analysis support (Feature #117)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=60)
    end_date = start_date + timedelta(days=60)

    # Create retained users (active within last 30 days)
    for i in range(5):
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="login",
            event_timestamp=end_date - timedelta(days=i),
            payload={"user_id": f"retained_user_{i}"},
        )
        db_session.add(event)

    # Create churned users (inactive for > 30 days)
    for i in range(3):
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="login",
            event_timestamp=end_date - timedelta(days=45 + i),
            payload={"user_id": f"churned_user_{i}"},
        )
        db_session.add(event)

    await db_session.flush()

    # Run retention analysis
    result = await advanced_analytics_service.retention_analysis(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        retention_period_days=30,
    )

    assert result["total_users"] == 8
    assert result["retained_users"] == 5
    assert result["churned_users"] == 3
    assert result["retention_rate"] > 0
    assert result["churn_rate"] > 0
    assert result["retention_rate"] + result["churn_rate"] == 100


@pytest.mark.asyncio
async def test_conversion_analysis(db_session: AsyncSession):
    """
    Test conversion funnel analysis.

    Features tested:
    - Conversion analysis support (Feature #118)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create funnel: dispatch -> on_scene -> transport_complete
    call_ids = [f"call_{i}" for i in range(20)]

    # All calls start with dispatch
    for call_id in call_ids:
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="dispatch",
            event_timestamp=start_date + timedelta(hours=call_ids.index(call_id)),
            payload={"call_id": call_id},
        )
        db_session.add(event)

    # 15 calls reach completion (75% conversion)
    for call_id in call_ids[:15]:
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="transport_complete",
            event_timestamp=start_date + timedelta(hours=call_ids.index(call_id) + 1),
            payload={"call_id": call_id},
        )
        db_session.add(event)

    await db_session.flush()

    # Run conversion analysis
    result = await advanced_analytics_service.conversion_analysis(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        conversion_event="transport_complete",
    )

    assert result["total_opportunities"] == 20
    assert result["conversions"] == 15
    assert result["conversion_rate"] == 75.0
    assert result["drop_off_rate"] == 25.0
    assert "funnel_stages" in result


@pytest.mark.asyncio
async def test_payer_lifecycle_analysis(db_session: AsyncSession):
    """
    Test payer lifecycle and relationship analysis.

    Features tested:
    - Payer lifecycle analysis (Feature #119)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=180)
    end_date = start_date + timedelta(days=180)

    # Create payer events spanning multiple months
    payer_ids = ["payer_A", "payer_B", "payer_C"]

    for payer_id in payer_ids:
        # Each payer has claims over a period
        claim_count = 10 + payer_ids.index(payer_id) * 5

        for i in range(claim_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="billing",
                event_type="claim_submitted",
                event_timestamp=start_date + timedelta(days=i * (180 // claim_count)),
                payload={"payer_id": payer_id, "claim_id": f"{payer_id}_claim_{i}"},
            )
            db_session.add(event)

    await db_session.flush()

    # Run lifecycle analysis
    result = await advanced_analytics_service.payer_lifecycle_analysis(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["total_payers"] == 3
    assert result["average_relationship_duration_days"] >= 0
    assert len(result["payer_metrics"]) == 3
    assert all("payer_id" in m for m in result["payer_metrics"])
    assert all("claim_count" in m for m in result["payer_metrics"])


@pytest.mark.asyncio
async def test_recurring_patient_analysis(db_session: AsyncSession):
    """
    Test recurring patient pattern analysis.

    Features tested:
    - Recurring patient analysis (Feature #120)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=60)
    end_date = start_date + timedelta(days=60)

    # Create patients with varying visit counts
    # 3 recurring patients (>= 3 visits)
    for patient_idx in range(3):
        for visit in range(5):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="epcr",
                event_type="patient_transport",
                event_timestamp=start_date + timedelta(days=visit * 10),
                payload={"patient_id": f"recurring_patient_{patient_idx}"},
            )
            db_session.add(event)

    # 5 non-recurring patients (< 3 visits)
    for patient_idx in range(5):
        for visit in range(2):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=start_date + timedelta(days=visit * 20),
                payload={"patient_id": f"occasional_patient_{patient_idx}"},
            )
            db_session.add(event)

    await db_session.flush()

    # Run recurring patient analysis
    result = await advanced_analytics_service.recurring_patient_analysis(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        recurrence_threshold=3,
    )

    assert result["total_patients"] == 8
    assert result["recurring_patients"] == 3
    assert result["recurring_rate"] > 0
    assert result["recurrence_threshold"] == 3
    assert len(result["most_frequent_patients"]) <= 10


@pytest.mark.asyncio
async def test_no_show_pattern_analysis(db_session: AsyncSession):
    """
    Test no-show and missed appointment analysis.

    Features tested:
    - Missed-appointment analysis (Feature #121)
    - No-show pattern analysis (Feature #122)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create scheduled appointments
    for i in range(100):
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="appointment_scheduled",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"appointment_id": f"appt_{i}"},
            )
        )

    # 10 no-shows
    for i in range(10):
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="appointment_no_show",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"appointment_id": f"appt_{i}"},
            )
        )

    # 15 cancellations
    for i in range(10, 25):
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="appointment_cancelled",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"appointment_id": f"appt_{i}"},
            )
        )

    await db_session.flush()

    # Run no-show analysis
    result = await advanced_analytics_service.no_show_pattern_analysis(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["total_scheduled"] == 100
    assert result["no_shows"] == 10
    assert result["cancellations"] == 15
    assert result["completed"] == 75
    assert result["no_show_rate"] == 10.0
    assert result["cancellation_rate"] == 15.0
    assert result["completion_rate"] == 75.0


@pytest.mark.asyncio
async def test_document_completion_lag_analysis(db_session: AsyncSession):
    """
    Test document completion lag time analysis.

    Features tested:
    - Document completion lag analysis (Feature #123)
    - Chart-signature lag analysis (Feature #124)
    - Export-readiness lag analysis (Feature #125)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create chart lifecycle events
    for i in range(50):
        chart_id = f"chart_{i}"
        created_time = start_date + timedelta(hours=i)

        # Chart created
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="epcr",
                event_type="chart_created",
                event_timestamp=created_time,
                payload={"chart_id": chart_id},
            )
        )

        # Chart completed (2-10 hours later)
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="epcr",
                event_type="chart_completed",
                event_timestamp=created_time + timedelta(hours=2 + (i % 8)),
                payload={"chart_id": chart_id},
            )
        )

        # Chart signed (4-12 hours later)
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="epcr",
                event_type="chart_signed",
                event_timestamp=created_time + timedelta(hours=4 + (i % 8)),
                payload={"chart_id": chart_id},
            )
        )

        # Chart exported (6-14 hours later)
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="epcr",
                event_type="chart_exported",
                event_timestamp=created_time + timedelta(hours=6 + (i % 8)),
                payload={"chart_id": chart_id},
            )
        )

    await db_session.flush()

    # Run lag analysis
    result = await advanced_analytics_service.document_completion_lag_analysis(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert "completion_lag" in result
    assert "signature_lag" in result
    assert "export_lag" in result
    assert result["total_charts_analyzed"] == 50

    # Verify lag metrics
    assert result["completion_lag"]["average_hours"] > 0
    assert result["signature_lag"]["average_hours"] > 0
    assert result["export_lag"]["average_hours"] > 0
    assert result["completion_lag"]["within_24h_percentage"] >= 0
