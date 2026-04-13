"""Tests for pattern detection service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models import AnalyticsEvent
from core_app.services.pattern_detection_service import pattern_detection_service


@pytest.mark.asyncio
async def test_seasonal_pattern_detection(db_session: AsyncSession):
    """
    Test seasonal pattern detection.

    Features tested:
    - Seasonal pattern detection (Feature #88)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)

    # Create events with seasonal variation
    for month in range(1, 13):
        # Summer months (6-8) have higher volume
        event_count = 100 if month in [6, 7, 8] else 50

        for i in range(event_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=datetime(2024, month, 1) + timedelta(hours=i),
                payload={"test": True},
            )
            db_session.add(event)

    await db_session.flush()

    # Detect seasonal patterns
    result = await pattern_detection_service.detect_seasonal_patterns(
        db=db_session,
        tenant_id=tenant_id,
        metric_name="call_volume",
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "seasonal"
    assert result["metric_name"] == "call_volume"
    assert "monthly_distribution" in result
    assert "peak_season" in result
    assert "low_season" in result
    assert result["peak_season"]["months"] == [6, 7, 8]


@pytest.mark.asyncio
async def test_day_of_week_pattern_detection(db_session: AsyncSession):
    """
    Test day-of-week pattern detection.

    Features tested:
    - Day-of-week pattern detection (Feature #89)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=28)
    end_date = start_date + timedelta(days=28)

    # Create events with weekday/weekend variation
    # Weekdays have more events
    current_date = start_date
    while current_date < end_date:
        event_count = 20 if current_date.weekday() < 5 else 10  # Mon-Fri vs Sat-Sun

        for i in range(event_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=current_date + timedelta(hours=i),
                payload={"test": True},
            )
            db_session.add(event)

        current_date += timedelta(days=1)

    await db_session.flush()

    # Detect day-of-week patterns
    result = await pattern_detection_service.detect_day_of_week_patterns(
        db=db_session,
        tenant_id=tenant_id,
        metric_name="call_volume",
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "day_of_week"
    assert result["metric_name"] == "call_volume"
    assert "daily_distribution" in result
    assert "busiest_day" in result
    assert "quietest_day" in result
    assert result["busiest_day"]["day_name"] in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


@pytest.mark.asyncio
async def test_hour_of_day_pattern_detection(db_session: AsyncSession):
    """
    Test hour-of-day pattern detection.

    Features tested:
    - Hour-of-day pattern detection (Feature #90)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
    end_date = start_date + timedelta(days=7)

    # Create events with peak hours (9 AM - 5 PM)
    for day in range(7):
        for hour in range(24):
            event_count = 10 if 9 <= hour <= 17 else 3

            for i in range(event_count):
                event = AnalyticsEvent(
                    tenant_id=tenant_id,
                    source_domain="cad",
                    event_type="dispatch",
                    event_timestamp=start_date + timedelta(days=day, hours=hour, minutes=i),
                    payload={"test": True},
                )
                db_session.add(event)

    await db_session.flush()

    # Detect hour-of-day patterns
    result = await pattern_detection_service.detect_hour_of_day_patterns(
        db=db_session,
        tenant_id=tenant_id,
        metric_name="call_volume",
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "hour_of_day"
    assert result["metric_name"] == "call_volume"
    assert "hourly_distribution" in result
    assert "peak_hours" in result
    assert "off_peak_hours" in result
    assert 9 <= result["peak_hours"]["hour"] <= 17


@pytest.mark.asyncio
async def test_incident_type_pattern_detection(db_session: AsyncSession):
    """
    Test incident type pattern detection.

    Features tested:
    - Incident-type pattern detection (Feature #91)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create events with various incident types
    incident_types = ["cardiac", "trauma", "respiratory", "stroke", "other"]
    incident_counts = [40, 25, 20, 10, 5]  # Decreasing frequency

    for incident_type, count in zip(incident_types, incident_counts):
        for i in range(count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"incident_type": incident_type},
            )
            db_session.add(event)

    await db_session.flush()

    # Detect incident type patterns
    result = await pattern_detection_service.detect_incident_type_patterns(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "incident_type"
    assert "incident_distribution" in result
    assert "most_common" in result
    assert result["most_common"]["incident_type"] == "cardiac"
    assert result["total_incidents"] == 100


@pytest.mark.asyncio
async def test_intervention_pattern_detection(db_session: AsyncSession):
    """
    Test intervention pattern detection.

    Features tested:
    - Intervention pattern detection (Feature #92)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create events with various interventions
    interventions = ["oxygen", "iv_access", "cpr", "aed", "splinting"]
    intervention_counts = [50, 40, 15, 10, 25]

    for intervention, count in zip(interventions, intervention_counts):
        for i in range(count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="epcr",
                event_type="intervention",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"intervention_type": intervention},
            )
            db_session.add(event)

    await db_session.flush()

    # Detect intervention patterns
    result = await pattern_detection_service.detect_intervention_patterns(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "intervention"
    assert "intervention_distribution" in result
    assert "most_common" in result
    assert result["most_common"]["intervention_type"] == "oxygen"


@pytest.mark.asyncio
async def test_medication_pattern_detection(db_session: AsyncSession):
    """
    Test medication administration pattern detection.

    Features tested:
    - Medication pattern detection (Feature #93)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create events with medication administrations
    medications = ["aspirin", "epinephrine", "naloxone", "nitroglycerin", "albuterol"]
    med_counts = [60, 20, 15, 25, 30]

    for medication, count in zip(medications, med_counts):
        for i in range(count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="epcr",
                event_type="medication_administered",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"medication": medication},
            )
            db_session.add(event)

    await db_session.flush()

    # Detect medication patterns
    result = await pattern_detection_service.detect_medication_patterns(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "medication"
    assert "medication_distribution" in result
    assert "most_common" in result
    assert result["most_common"]["medication"] == "aspirin"


@pytest.mark.asyncio
async def test_destination_pattern_detection(db_session: AsyncSession):
    """
    Test destination facility pattern detection.

    Features tested:
    - Destination pattern detection (Feature #94)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create transport events to various facilities
    facilities = ["Hospital_A", "Hospital_B", "Hospital_C", "Clinic_D"]
    facility_counts = [50, 30, 15, 5]

    for facility, count in zip(facilities, facility_counts):
        for i in range(count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="transport_complete",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"destination": facility},
            )
            db_session.add(event)

    await db_session.flush()

    # Detect destination patterns
    result = await pattern_detection_service.detect_destination_patterns(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "destination"
    assert "destination_distribution" in result
    assert "most_common" in result
    assert result["most_common"]["destination"] == "Hospital_A"
    assert result["total_transports"] == 100


@pytest.mark.asyncio
async def test_staffing_trend_detection(db_session: AsyncSession):
    """
    Test staffing level trend detection.

    Features tested:
    - Staffing-trend detection (Feature #95)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=60)
    end_date = start_date + timedelta(days=60)

    # Create staffing events with increasing trend
    for day in range(60):
        crew_count = 10 + (day // 10)  # Gradually increasing

        for crew_idx in range(crew_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="shift_start",
                event_timestamp=start_date + timedelta(days=day, hours=crew_idx % 24),
                payload={"crew_id": f"crew_{crew_idx}"},
            )
            db_session.add(event)

    await db_session.flush()

    # Detect staffing trends
    result = await pattern_detection_service.detect_staffing_trends(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "staffing_trend"
    assert "daily_staffing" in result
    assert "average_staff" in result
    assert "trend" in result
    assert result["trend"] in ["increasing", "decreasing", "stable"]


@pytest.mark.asyncio
async def test_geographic_pattern_detection(db_session: AsyncSession):
    """
    Test geographic hotspot detection.

    Features tested:
    - Geographic hotspot detection (Feature #96)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create events in various zones
    zones = ["Zone_1", "Zone_2", "Zone_3", "Zone_4"]
    zone_counts = [60, 25, 10, 5]

    for zone, count in zip(zones, zone_counts):
        for i in range(count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"zone": zone},
            )
            db_session.add(event)

    await db_session.flush()

    # Detect geographic patterns
    result = await pattern_detection_service.detect_geographic_patterns(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "geographic"
    assert "zone_distribution" in result
    assert "hotspot" in result
    assert result["hotspot"]["zone"] == "Zone_1"


@pytest.mark.asyncio
async def test_response_time_pattern_detection(db_session: AsyncSession):
    """
    Test response time pattern detection.

    Features tested:
    - Response-time pattern detection (Feature #97)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create dispatch and arrival events with varying response times
    for i in range(100):
        dispatch_time = start_date + timedelta(hours=i)
        response_minutes = 5 + (i % 10)  # Varies 5-14 minutes

        # Dispatch event
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=dispatch_time,
                payload={"call_id": f"call_{i}"},
            )
        )

        # Arrival event
        db_session.add(
            AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="on_scene",
                event_timestamp=dispatch_time + timedelta(minutes=response_minutes),
                payload={"call_id": f"call_{i}", "response_time_minutes": response_minutes},
            )
        )

    await db_session.flush()

    # Detect response time patterns
    result = await pattern_detection_service.detect_response_time_patterns(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "response_time"
    assert "average_response_time" in result
    assert result["total_calls"] == 100


@pytest.mark.asyncio
async def test_unit_utilization_pattern_detection(db_session: AsyncSession):
    """
    Test unit utilization pattern detection.

    Features tested:
    - Unit-utilization pattern detection (Feature #98)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=7)
    end_date = start_date + timedelta(days=7)

    # Create events for different units with varying activity
    units = ["Unit_A", "Unit_B", "Unit_C"]
    unit_event_counts = [100, 60, 30]

    for unit_id, event_count in zip(units, unit_event_counts):
        for i in range(event_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="dispatch",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"unit_id": unit_id},
            )
            db_session.add(event)

    await db_session.flush()

    # Detect utilization patterns
    result = await pattern_detection_service.detect_unit_utilization_patterns(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "unit_utilization"
    assert "unit_activity" in result
    assert "most_utilized" in result
    assert result["most_utilized"]["unit_id"] == "Unit_A"


@pytest.mark.asyncio
async def test_billing_denial_pattern_detection(db_session: AsyncSession):
    """
    Test billing denial pattern detection.

    Features tested:
    - Billing-denial pattern detection (Feature #99)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=60)
    end_date = start_date + timedelta(days=60)

    # Create billing events with denials
    denial_reasons = ["incomplete_docs", "authorization", "coding_error", "duplicate"]
    denial_counts = [40, 25, 20, 15]

    for reason, count in zip(denial_reasons, denial_counts):
        for i in range(count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="billing",
                event_type="claim_denied",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"denial_reason": reason},
            )
            db_session.add(event)

    await db_session.flush()

    # Detect denial patterns
    result = await pattern_detection_service.detect_billing_denial_patterns(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "billing_denial"
    assert "denial_distribution" in result
    assert "most_common_reason" in result
    assert result["most_common_reason"]["reason"] == "incomplete_docs"
    assert result["total_denials"] == 100


@pytest.mark.asyncio
async def test_crew_performance_pattern_detection(db_session: AsyncSession):
    """
    Test crew performance pattern detection.

    Features tested:
    - Crew-performance pattern detection (Feature #100)
    """
    tenant_id = uuid.uuid4()
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=30)
    end_date = start_date + timedelta(days=30)

    # Create events for different crews
    crews = ["Crew_A", "Crew_B", "Crew_C"]
    crew_event_counts = [80, 60, 40]

    for crew_id, event_count in zip(crews, crew_event_counts):
        for i in range(event_count):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain="cad",
                event_type="transport_complete",
                event_timestamp=start_date + timedelta(hours=i),
                payload={"crew_id": crew_id},
            )
            db_session.add(event)

    await db_session.flush()

    # Detect crew performance patterns
    result = await pattern_detection_service.detect_crew_performance_patterns(
        db=db_session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert result["pattern_type"] == "crew_performance"
    assert "crew_activity" in result
    assert "top_performer" in result
    assert result["top_performer"]["crew_id"] == "Crew_A"
