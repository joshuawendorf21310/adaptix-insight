"""Tests for aggregation service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models import AggregationLevel, AnalyticsEvent, DomainRollup, TenantRollup
from core_app.services.aggregation_service import aggregation_service


@pytest.mark.asyncio
async def test_domain_rollup_aggregation(db_session: AsyncSession):
    """
    Test domain-level aggregation.

    Features tested:
    - Domain rollup pipeline (Feature #18)
    - Daily aggregation pipeline (Feature #21)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = now + timedelta(days=1)

    # Create test events
    for i in range(5):
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="dispatch",
            event_timestamp=now + timedelta(hours=i),
            payload={"unit_id": f"E10{i}"},
        )
        db_session.add(event)
    await db_session.flush()

    # Run aggregation
    rollup = await aggregation_service.aggregate_domain_rollup(
        db=db_session,
        tenant_id=tenant_id,
        source_domain="cad",
        aggregation_level=AggregationLevel.DAILY,
        period_start=now,
        period_end=period_end,
    )

    assert rollup.tenant_id == tenant_id
    assert rollup.source_domain == "cad"
    assert rollup.aggregation_level == AggregationLevel.DAILY.value
    assert rollup.event_count == 5
    assert rollup.metrics["event_count"] == 5
    assert rollup.metrics["unique_event_types"] == 1
    assert rollup.metrics["event_types"]["dispatch"] == 5


@pytest.mark.asyncio
async def test_tenant_rollup_aggregation(db_session: AsyncSession):
    """
    Test tenant-level aggregation across domains.

    Features tested:
    - Tenant rollup pipeline (Feature #19)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = now + timedelta(days=1)

    # Create domain rollups
    domains = ["cad", "epcr", "billing"]
    for domain in domains:
        rollup = DomainRollup(
            tenant_id=tenant_id,
            source_domain=domain,
            aggregation_level=AggregationLevel.DAILY.value,
            period_start=now,
            period_end=period_end,
            metrics={"event_count": 10},
            event_count=10,
        )
        db_session.add(rollup)
    await db_session.flush()

    # Run tenant aggregation
    tenant_rollup = await aggregation_service.aggregate_tenant_rollup(
        db=db_session,
        tenant_id=tenant_id,
        aggregation_level=AggregationLevel.DAILY,
        period_start=now,
        period_end=period_end,
    )

    assert tenant_rollup.tenant_id == tenant_id
    assert tenant_rollup.event_count == 30  # 10 events per domain * 3 domains
    assert tenant_rollup.metrics["total_events"] == 30
    assert tenant_rollup.metrics["domain_count"] == 3
    assert tenant_rollup.domain_breakdown["cad"] == 10
    assert tenant_rollup.domain_breakdown["epcr"] == 10
    assert tenant_rollup.domain_breakdown["billing"] == 10


@pytest.mark.asyncio
async def test_consistency_check(db_session: AsyncSession):
    """
    Test aggregation consistency checking.

    Features tested:
    - Analytics consistency checks (Feature #30)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    period_end = now + timedelta(days=1)

    # Create 10 raw events
    for i in range(10):
        event = AnalyticsEvent(
            tenant_id=tenant_id,
            source_domain="cad",
            event_type="dispatch",
            event_timestamp=now + timedelta(hours=i),
            payload={"index": i},
        )
        db_session.add(event)
    await db_session.flush()

    # Create tenant rollup with matching count
    tenant_rollup = TenantRollup(
        tenant_id=tenant_id,
        aggregation_level=AggregationLevel.DAILY.value,
        period_start=now,
        period_end=period_end,
        metrics={"total_events": 10},
        domain_breakdown={"cad": 10},
        event_count=10,
    )
    db_session.add(tenant_rollup)
    await db_session.flush()

    # Check consistency
    result = await aggregation_service.check_consistency(
        db=db_session,
        tenant_id=tenant_id,
        period_start=now,
        period_end=period_end,
    )

    assert result["consistent"] is True
    assert result["raw_count"] == 10
    assert result["rollup_count"] == 10
    assert result["difference"] == 0


@pytest.mark.asyncio
async def test_daily_aggregation_workflow(db_session: AsyncSession):
    """
    Test complete daily aggregation workflow.

    Features tested:
    - Daily aggregation pipeline (Feature #21)
    - End-to-end aggregation flow
    """
    tenant_id = uuid.uuid4()
    target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Create events across multiple domains
    domains = ["cad", "epcr"]
    for domain in domains:
        for i in range(3):
            event = AnalyticsEvent(
                tenant_id=tenant_id,
                source_domain=domain,
                event_type="test_event",
                event_timestamp=target_date + timedelta(hours=i),
                payload={"test": True},
            )
            db_session.add(event)
    await db_session.flush()

    # Run daily aggregation
    await aggregation_service.run_daily_aggregation(
        db=db_session,
        tenant_id=tenant_id,
        target_date=target_date,
    )

    # Verify domain rollups created
    for domain in domains:
        from sqlalchemy import select

        query = select(DomainRollup).where(
            DomainRollup.tenant_id == tenant_id,
            DomainRollup.source_domain == domain,
            DomainRollup.period_start == target_date,
        )
        result = await db_session.execute(query)
        rollup = result.scalar_one_or_none()
        assert rollup is not None
        assert rollup.event_count == 3

    # Verify tenant rollup created
    from sqlalchemy import select

    query = select(TenantRollup).where(
        TenantRollup.tenant_id == tenant_id,
        TenantRollup.period_start == target_date,
    )
    result = await db_session.execute(query)
    tenant_rollup = result.scalar_one_or_none()
    assert tenant_rollup is not None
    assert tenant_rollup.event_count == 6  # 3 events per domain * 2 domains
