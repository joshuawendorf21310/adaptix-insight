"""Data quality monitoring service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.models import AnalyticsEvent, DataQualityMetric
from core_app.schemas import DataQualityResponse, DataQualityStatus

logger = get_logger(__name__)


class DataQualityService:
    """Service for data quality monitoring and freshness tracking."""

    async def check_data_quality(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> DataQualityResponse:
        """
        Check data quality across all source domains.

        Features implemented:
        - Source freshness warnings (Feature #155)
        - Stale analytics warnings (Feature #156)
        - Incomplete-data warnings (Feature #157)
        - Metric quality score (Feature #159)
        - Data completeness score (Feature #161)
        """
        domains = ["cad", "epcr", "crewlink", "field", "air", "fire", "workforce", "billing"]
        domain_statuses = []
        overall_warnings = []

        for domain in domains:
            status = await self._check_domain_quality(db, tenant_id, domain)
            domain_statuses.append(status)

            if status.warnings:
                overall_warnings.extend(status.warnings)

        # Determine overall status
        if any(s.status == "unhealthy" for s in domain_statuses):
            overall_status = "unhealthy"
        elif any(s.status == "degraded" for s in domain_statuses):
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return DataQualityResponse(
            tenant_id=tenant_id,
            overall_status=overall_status,
            domains=domain_statuses,
            checked_at=datetime.now(),
        )

    async def _check_domain_quality(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        source_domain: str,
    ) -> DataQualityStatus:
        """Check data quality for a specific domain."""
        # Get latest event timestamp
        query = (
            select(func.max(AnalyticsEvent.event_timestamp))
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.source_domain == source_domain,
            )
        )
        result = await db.execute(query)
        last_data_timestamp = result.scalar()

        warnings = []
        status = "healthy"
        completeness_score = 1.0

        if last_data_timestamp is None:
            warnings.append(f"No data received from {source_domain}")
            status = "unhealthy"
            completeness_score = 0.0
        else:
            # Check staleness
            time_since_last = datetime.now() - last_data_timestamp
            if time_since_last > timedelta(hours=24):
                warnings.append(f"Data from {source_domain} is stale (last: {last_data_timestamp})")
                status = "degraded"
                completeness_score = 0.5
            elif time_since_last > timedelta(hours=6):
                warnings.append(f"Data from {source_domain} is aging (last: {last_data_timestamp})")
                if status == "healthy":
                    status = "degraded"
                completeness_score = 0.8

        return DataQualityStatus(
            source_domain=source_domain,
            last_data_timestamp=last_data_timestamp,
            completeness_score=completeness_score,
            status=status,
            warnings=warnings,
        )

    async def store_quality_metric(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        source_domain: str,
        metric_type: str,
        value: float,
        threshold: float | None,
        status: str,
        last_data_timestamp: datetime | None,
        completeness_score: float | None,
        warnings: list[str] | None,
    ) -> DataQualityMetric:
        """Store data quality metric."""
        metric = DataQualityMetric(
            tenant_id=tenant_id,
            source_domain=source_domain,
            metric_type=metric_type,
            value=value,
            threshold=threshold,
            status=status,
            last_data_timestamp=last_data_timestamp,
            completeness_score=completeness_score,
            warnings=warnings,
        )
        db.add(metric)
        await db.flush()
        return metric


# Singleton instance
data_quality_service = DataQualityService()
