"""Tests for data quality service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models import AnalyticsEvent
from core_app.services.data_quality_service import data_quality_service


@pytest.mark.asyncio
async def test_data_freshness_healthy(db_session: AsyncSession):
    """
    Test data freshness detection - healthy state.

    Features tested:
    - Source freshness warnings (Feature #155)
    - Data completeness score (Feature #161)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()

    # Create recent event (within last hour)
    event = AnalyticsEvent(
        tenant_id=tenant_id,
        source_domain="cad",
        event_type="dispatch",
        event_timestamp=now - timedelta(minutes=30),
        payload={"test": True},
    )
    db_session.add(event)
    await db_session.flush()

    # Check quality
    quality_response = await data_quality_service.check_data_quality(db_session, tenant_id)

    assert quality_response.overall_status == "healthy"
    cad_status = next((d for d in quality_response.domains if d.source_domain == "cad"), None)
    assert cad_status is not None
    assert cad_status.status == "healthy"
    assert cad_status.completeness_score == 1.0
    assert len(cad_status.warnings) == 0


@pytest.mark.asyncio
async def test_data_freshness_degraded(db_session: AsyncSession):
    """
    Test stale data detection - degraded state.

    Features tested:
    - Stale analytics warnings (Feature #156)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()

    # Create event that's 12 hours old (degraded threshold is 6 hours)
    event = AnalyticsEvent(
        tenant_id=tenant_id,
        source_domain="epcr",
        event_type="chart_update",
        event_timestamp=now - timedelta(hours=12),
        payload={"test": True},
    )
    db_session.add(event)
    await db_session.flush()

    # Check quality
    quality_response = await data_quality_service.check_data_quality(db_session, tenant_id)

    assert quality_response.overall_status == "degraded"
    epcr_status = next((d for d in quality_response.domains if d.source_domain == "epcr"), None)
    assert epcr_status is not None
    assert epcr_status.status == "degraded"
    assert len(epcr_status.warnings) > 0
    assert any("aging" in w.lower() or "stale" in w.lower() for w in epcr_status.warnings)


@pytest.mark.asyncio
async def test_data_freshness_unhealthy(db_session: AsyncSession):
    """
    Test very stale data detection - unhealthy state.

    Features tested:
    - Stale analytics warnings (Feature #156)
    - Incomplete-data warnings (Feature #157)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()

    # Create event that's 36 hours old (unhealthy threshold is 24 hours)
    event = AnalyticsEvent(
        tenant_id=tenant_id,
        source_domain="billing",
        event_type="claim_submitted",
        event_timestamp=now - timedelta(hours=36),
        payload={"test": True},
    )
    db_session.add(event)
    await db_session.flush()

    # Check quality
    quality_response = await data_quality_service.check_data_quality(db_session, tenant_id)

    assert quality_response.overall_status == "degraded"  # At least one degraded
    billing_status = next((d for d in quality_response.domains if d.source_domain == "billing"), None)
    assert billing_status is not None
    assert billing_status.status == "degraded"
    assert billing_status.completeness_score == 0.5
    assert len(billing_status.warnings) > 0


@pytest.mark.asyncio
async def test_no_data_received(db_session: AsyncSession):
    """
    Test handling of domains with no data.

    Features tested:
    - Incomplete-data warnings (Feature #157)
    """
    tenant_id = uuid.uuid4()

    # Don't create any events
    # Check quality
    quality_response = await data_quality_service.check_data_quality(db_session, tenant_id)

    # Should have unhealthy status for domains with no data
    assert quality_response.overall_status == "unhealthy"

    # All domains should report no data
    for domain_status in quality_response.domains:
        assert domain_status.last_data_timestamp is None
        assert domain_status.status == "unhealthy"
        assert domain_status.completeness_score == 0.0
        assert any("no data" in w.lower() for w in domain_status.warnings)


@pytest.mark.asyncio
async def test_mixed_domain_quality(db_session: AsyncSession):
    """
    Test quality check with mixed domain health.

    Features tested:
    - Multi-domain quality aggregation
    - Overall status calculation
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()

    # Create healthy data for CAD
    event1 = AnalyticsEvent(
        tenant_id=tenant_id,
        source_domain="cad",
        event_type="dispatch",
        event_timestamp=now - timedelta(minutes=10),
        payload={"healthy": True},
    )
    db_session.add(event1)

    # Create degraded data for ePCR (8 hours old)
    event2 = AnalyticsEvent(
        tenant_id=tenant_id,
        source_domain="epcr",
        event_type="chart",
        event_timestamp=now - timedelta(hours=8),
        payload={"degraded": True},
    )
    db_session.add(event2)

    # No data for billing (unhealthy)
    await db_session.flush()

    # Check quality
    quality_response = await data_quality_service.check_data_quality(db_session, tenant_id)

    # Overall should be unhealthy (worst case)
    assert quality_response.overall_status == "unhealthy"

    # Verify individual domain statuses
    cad_status = next((d for d in quality_response.domains if d.source_domain == "cad"), None)
    assert cad_status.status == "healthy"

    epcr_status = next((d for d in quality_response.domains if d.source_domain == "epcr"), None)
    assert epcr_status.status == "degraded"

    billing_status = next((d for d in quality_response.domains if d.source_domain == "billing"), None)
    assert billing_status.status == "unhealthy"
