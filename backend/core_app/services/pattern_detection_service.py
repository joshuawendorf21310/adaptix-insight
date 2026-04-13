"""Pattern detection and trend analysis service."""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.models import AnalyticsEvent

logger = get_logger(__name__)


class PatternDetectionService:
    """Service for pattern detection and trend analysis."""

    async def detect_seasonal_patterns(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        metric_name: str,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Detect seasonal patterns in metrics.

        Feature #88: Seasonal pattern detection
        """
        # Query events grouped by month
        query = (
            select(
                func.extract("month", AnalyticsEvent.event_timestamp).label("month"),
                func.count(AnalyticsEvent.id).label("event_count"),
            )
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp < end_date,
            )
            .group_by(func.extract("month", AnalyticsEvent.event_timestamp))
        )

        result = await db.execute(query)
        monthly_data = {int(row.month): row.event_count for row in result.all()}

        # Calculate seasonal indices
        avg_count = sum(monthly_data.values()) / len(monthly_data) if monthly_data else 0
        seasonal_indices = {month: count / avg_count if avg_count > 0 else 1.0 for month, count in monthly_data.items()}

        # Identify peak and low seasons
        peak_month = max(seasonal_indices.items(), key=lambda x: x[1])[0] if seasonal_indices else None
        low_month = min(seasonal_indices.items(), key=lambda x: x[1])[0] if seasonal_indices else None

        return {
            "metric_name": metric_name,
            "analysis_period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "seasonal_indices": seasonal_indices,
            "peak_month": peak_month,
            "low_month": low_month,
            "seasonality_strength": max(seasonal_indices.values()) / min(seasonal_indices.values())
            if seasonal_indices
            else 1.0,
        }

    async def detect_day_of_week_patterns(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Detect day-of-week patterns.

        Feature #89: Day-of-week pattern detection
        """
        query = (
            select(
                func.extract("dow", AnalyticsEvent.event_timestamp).label("day_of_week"),
                func.count(AnalyticsEvent.id).label("event_count"),
            )
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp < end_date,
            )
            .group_by(func.extract("dow", AnalyticsEvent.event_timestamp))
        )

        result = await db.execute(query)
        dow_data = {int(row.day_of_week): row.event_count for row in result.all()}

        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        patterns = {day_names[dow]: count for dow, count in dow_data.items()}

        avg_count = sum(dow_data.values()) / len(dow_data) if dow_data else 0
        busiest_day = max(patterns.items(), key=lambda x: x[1])[0] if patterns else None
        quietest_day = min(patterns.items(), key=lambda x: x[1])[0] if patterns else None

        return {
            "patterns": patterns,
            "average_daily_count": avg_count,
            "busiest_day": busiest_day,
            "quietest_day": quietest_day,
            "weekday_vs_weekend": self._calculate_weekday_weekend_ratio(dow_data),
        }

    async def detect_hour_of_day_patterns(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Detect hour-of-day patterns.

        Feature #90: Hour-of-day pattern detection
        """
        query = (
            select(
                func.extract("hour", AnalyticsEvent.event_timestamp).label("hour"),
                func.count(AnalyticsEvent.id).label("event_count"),
            )
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp < end_date,
            )
            .group_by(func.extract("hour", AnalyticsEvent.event_timestamp))
        )

        result = await db.execute(query)
        hourly_data = {int(row.hour): row.event_count for row in result.all()}

        peak_hour = max(hourly_data.items(), key=lambda x: x[1])[0] if hourly_data else None
        low_hour = min(hourly_data.items(), key=lambda x: x[1])[0] if hourly_data else None

        return {
            "hourly_distribution": hourly_data,
            "peak_hour": peak_hour,
            "low_hour": low_hour,
            "peak_periods": self._identify_peak_periods(hourly_data),
        }

    async def analyze_incident_type_mix(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        source_domain: str,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Analyze incident type distribution.

        Feature #92: Incident type mix analysis
        """
        query = select(AnalyticsEvent.payload).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain == source_domain,
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        # Extract incident types from payloads
        incident_types = [event.get("incident_type") for event in events if event.get("incident_type")]
        type_counts = Counter(incident_types)

        total = len(incident_types)
        mix_percentages = {itype: (count / total * 100) if total > 0 else 0 for itype, count in type_counts.items()}

        return {
            "total_incidents": total,
            "incident_types": dict(type_counts),
            "mix_percentages": mix_percentages,
            "most_common": type_counts.most_common(5),
            "diversity_index": len(type_counts),
        }

    async def analyze_intervention_frequency(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Analyze intervention frequency.

        Features #93-94: Intervention frequency analysis, most-used interventions
        """
        query = select(AnalyticsEvent.payload).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain == "epcr",
            AnalyticsEvent.event_type == "intervention",
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        interventions = [event.get("intervention_code") for event in events if event.get("intervention_code")]
        intervention_counts = Counter(interventions)

        return {
            "total_interventions": len(interventions),
            "unique_interventions": len(intervention_counts),
            "intervention_counts": dict(intervention_counts),
            "most_used": intervention_counts.most_common(10),
            "average_interventions_per_call": len(interventions) / len(set([e.get("call_id") for e in events]))
            if events
            else 0,
        }

    async def analyze_medication_frequency(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Analyze medication administration frequency.

        Feature #95: Medication frequency analysis
        """
        query = select(AnalyticsEvent.payload).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain == "epcr",
            AnalyticsEvent.event_type == "medication_administered",
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        medications = [event.get("medication_name") for event in events if event.get("medication_name")]
        medication_counts = Counter(medications)

        return {
            "total_administrations": len(medications),
            "unique_medications": len(medication_counts),
            "medication_counts": dict(medication_counts),
            "most_administered": medication_counts.most_common(10),
            "top_10_coverage_percentage": sum(count for _, count in medication_counts.most_common(10))
            / len(medications)
            * 100
            if medications
            else 0,
        }

    async def analyze_destination_patterns(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Analyze destination facility patterns.

        Feature #96: Destination pattern analysis
        """
        query = select(AnalyticsEvent.payload).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain == "cad",
            AnalyticsEvent.event_type.in_(["transport", "transport_complete"]),
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        destinations = [event.get("destination_facility") for event in events if event.get("destination_facility")]
        destination_counts = Counter(destinations)

        return {
            "total_transports": len(destinations),
            "unique_destinations": len(destination_counts),
            "destination_distribution": dict(destination_counts),
            "top_destinations": destination_counts.most_common(10),
            "facility_utilization": {
                dest: (count / len(destinations) * 100) if destinations else 0
                for dest, count in destination_counts.items()
            },
        }

    async def analyze_staffing_shortage_trends(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Analyze staffing shortage trends over time.

        Feature #97: Staffing shortage trend analysis
        """
        query = select(AnalyticsEvent.event_timestamp, AnalyticsEvent.payload).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain == "workforce",
            AnalyticsEvent.event_type == "staffing_shortage",
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.all()

        # Group by week
        weekly_shortages = defaultdict(int)
        for event in events:
            week_key = event.event_timestamp.strftime("%Y-W%W")
            weekly_shortages[week_key] += 1

        trend = "increasing" if self._is_increasing_trend(list(weekly_shortages.values())) else "stable"

        return {
            "total_shortage_events": len(events),
            "weekly_distribution": dict(weekly_shortages),
            "trend": trend,
            "average_per_week": sum(weekly_shortages.values()) / len(weekly_shortages) if weekly_shortages else 0,
            "peak_week": max(weekly_shortages.items(), key=lambda x: x[1])[0] if weekly_shortages else None,
        }

    def _calculate_weekday_weekend_ratio(self, dow_data: dict[int, int]) -> dict[str, float]:
        """Calculate weekday vs weekend ratio."""
        weekday_total = sum(count for dow, count in dow_data.items() if 1 <= dow <= 5)
        weekend_total = sum(count for dow, count in dow_data.items() if dow in [0, 6])
        total = weekday_total + weekend_total

        return {
            "weekday_percentage": (weekday_total / total * 100) if total > 0 else 0,
            "weekend_percentage": (weekend_total / total * 100) if total > 0 else 0,
            "ratio": (weekday_total / weekend_total) if weekend_total > 0 else 0,
        }

    def _identify_peak_periods(self, hourly_data: dict[int, int]) -> list[str]:
        """Identify peak time periods."""
        avg = sum(hourly_data.values()) / len(hourly_data) if hourly_data else 0
        peak_hours = [hour for hour, count in hourly_data.items() if count > avg * 1.5]

        periods = []
        if any(6 <= h < 12 for h in peak_hours):
            periods.append("morning")
        if any(12 <= h < 18 for h in peak_hours):
            periods.append("afternoon")
        if any(18 <= h < 24 for h in peak_hours):
            periods.append("evening")
        if any(0 <= h < 6 for h in peak_hours):
            periods.append("night")

        return periods

    def _is_increasing_trend(self, values: list[int]) -> bool:
        """Simple trend detection."""
        if len(values) < 2:
            return False
        first_half_avg = sum(values[: len(values) // 2]) / (len(values) // 2)
        second_half_avg = sum(values[len(values) // 2 :]) / (len(values) - len(values) // 2)
        return second_half_avg > first_half_avg * 1.1


# Singleton instance
pattern_detection_service = PatternDetectionService()
