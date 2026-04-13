"""Aggregation and rollup pipeline service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.models import AggregationLevel, AnalyticsEvent, DomainRollup, TenantRollup

logger = get_logger(__name__)


class AggregationService:
    """Service for analytics aggregation and rollup pipelines."""

    async def aggregate_domain_rollup(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        source_domain: str,
        aggregation_level: AggregationLevel,
        period_start: datetime,
        period_end: datetime,
    ) -> DomainRollup:
        """
        Create domain-level aggregation.

        Features implemented:
        - Domain rollup pipeline (Feature #18)
        - Daily aggregation pipeline (Feature #21)
        - Weekly aggregation pipeline (Feature #22)
        - Monthly aggregation pipeline (Feature #23)
        - Quarterly aggregation pipeline (Feature #24)
        - Yearly aggregation pipeline (Feature #25)
        """
        # Query analytics events for the period
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain == source_domain,
            AnalyticsEvent.event_timestamp >= period_start,
            AnalyticsEvent.event_timestamp < period_end,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        # Aggregate metrics from events
        event_count = len(events)
        event_types = {}
        for event in events:
            event_type = event.event_type
            event_types[event_type] = event_types.get(event_type, 0) + 1

        metrics = {
            "event_count": event_count,
            "event_types": event_types,
            "unique_event_types": len(event_types),
        }

        # Check if rollup exists
        existing = await db.execute(
            select(DomainRollup).where(
                DomainRollup.tenant_id == tenant_id,
                DomainRollup.source_domain == source_domain,
                DomainRollup.aggregation_level == aggregation_level.value,
                DomainRollup.period_start == period_start,
            )
        )
        rollup = existing.scalar_one_or_none()

        if rollup:
            # Update existing
            rollup.metrics = metrics
            rollup.event_count = event_count
            rollup.period_end = period_end
            rollup.updated_at = datetime.now()
        else:
            # Create new
            rollup = DomainRollup(
                tenant_id=tenant_id,
                source_domain=source_domain,
                aggregation_level=aggregation_level.value,
                period_start=period_start,
                period_end=period_end,
                metrics=metrics,
                event_count=event_count,
            )
            db.add(rollup)

        await db.flush()
        logger.info(
            "domain_rollup_aggregated",
            tenant_id=str(tenant_id),
            source_domain=source_domain,
            aggregation_level=aggregation_level.value,
            event_count=event_count,
        )

        return rollup

    async def aggregate_tenant_rollup(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        aggregation_level: AggregationLevel,
        period_start: datetime,
        period_end: datetime,
    ) -> TenantRollup:
        """
        Create tenant-level aggregation across all domains.

        Features implemented:
        - Tenant rollup pipeline (Feature #19)
        """
        # Query all domain rollups for this period
        query = select(DomainRollup).where(
            DomainRollup.tenant_id == tenant_id,
            DomainRollup.aggregation_level == aggregation_level.value,
            DomainRollup.period_start == period_start,
        )

        result = await db.execute(query)
        domain_rollups = result.scalars().all()

        # Aggregate across domains
        total_events = sum(dr.event_count for dr in domain_rollups)
        domain_breakdown = {dr.source_domain: dr.event_count for dr in domain_rollups}

        metrics = {
            "total_events": total_events,
            "domain_count": len(domain_rollups),
        }

        # Check if tenant rollup exists
        existing = await db.execute(
            select(TenantRollup).where(
                TenantRollup.tenant_id == tenant_id,
                TenantRollup.aggregation_level == aggregation_level.value,
                TenantRollup.period_start == period_start,
            )
        )
        rollup = existing.scalar_one_or_none()

        if rollup:
            # Update existing
            rollup.metrics = metrics
            rollup.domain_breakdown = domain_breakdown
            rollup.event_count = total_events
            rollup.period_end = period_end
            rollup.updated_at = datetime.now()
        else:
            # Create new
            rollup = TenantRollup(
                tenant_id=tenant_id,
                aggregation_level=aggregation_level.value,
                period_start=period_start,
                period_end=period_end,
                metrics=metrics,
                domain_breakdown=domain_breakdown,
                event_count=total_events,
            )
            db.add(rollup)

        await db.flush()
        logger.info(
            "tenant_rollup_aggregated",
            tenant_id=str(tenant_id),
            aggregation_level=aggregation_level.value,
            event_count=total_events,
        )

        return rollup

    async def run_daily_aggregation(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        target_date: datetime,
    ) -> None:
        """
        Run daily aggregation for all domains.

        Feature #21: Daily aggregation pipeline
        """
        period_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=1)

        # Aggregate each domain
        domains = ["cad", "epcr", "crewlink", "field", "air", "fire", "workforce", "billing"]

        for domain in domains:
            await self.aggregate_domain_rollup(
                db=db,
                tenant_id=tenant_id,
                source_domain=domain,
                aggregation_level=AggregationLevel.DAILY,
                period_start=period_start,
                period_end=period_end,
            )

        # Aggregate tenant-level
        await self.aggregate_tenant_rollup(
            db=db,
            tenant_id=tenant_id,
            aggregation_level=AggregationLevel.DAILY,
            period_start=period_start,
            period_end=period_end,
        )

        logger.info("daily_aggregation_completed", tenant_id=str(tenant_id), date=target_date.date())

    async def check_consistency(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """
        Check aggregation consistency.

        Feature #30: Analytics consistency checks
        """
        # Count raw events
        raw_count_query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.event_timestamp >= period_start,
            AnalyticsEvent.event_timestamp < period_end,
        )
        raw_result = await db.execute(raw_count_query)
        raw_count = len(raw_result.scalars().all())

        # Get tenant rollup
        rollup_query = select(TenantRollup).where(
            TenantRollup.tenant_id == tenant_id,
            TenantRollup.period_start == period_start,
        )
        rollup_result = await db.execute(rollup_query)
        rollup = rollup_result.scalar_one_or_none()

        if not rollup:
            return {
                "consistent": False,
                "reason": "missing_rollup",
                "raw_count": raw_count,
                "rollup_count": 0,
            }

        is_consistent = raw_count == rollup.event_count
        return {
            "consistent": is_consistent,
            "raw_count": raw_count,
            "rollup_count": rollup.event_count,
            "difference": abs(raw_count - rollup.event_count),
        }


# Singleton instance
aggregation_service = AggregationService()
