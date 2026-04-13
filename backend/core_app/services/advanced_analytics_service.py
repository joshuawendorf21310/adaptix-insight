"""Advanced analytics service for cohort, retention, and conversion analysis."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.models import AnalyticsEvent

logger = get_logger(__name__)


class AdvancedAnalyticsService:
    """Service for advanced analytics including cohort, retention, and conversion analysis."""

    async def cohort_analysis(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        cohort_start: datetime,
        cohort_end: datetime,
        metric: str = "retention",
    ) -> dict[str, Any]:
        """
        Perform cohort analysis.

        Feature #116: Cohort analysis support
        """
        # Query events grouped by cohort (e.g., month of first interaction)
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.event_timestamp >= cohort_start,
            AnalyticsEvent.event_timestamp < cohort_end,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        # Group by user/entity and cohort month
        user_cohorts = defaultdict(lambda: {"first_seen": None, "events": []})

        for event in events:
            user_id = event.payload.get("user_id") or event.payload.get("patient_id")
            if not user_id:
                continue

            if user_cohorts[user_id]["first_seen"] is None:
                user_cohorts[user_id]["first_seen"] = event.event_timestamp
            user_cohorts[user_id]["events"].append(event.event_timestamp)

        # Build cohort matrix
        cohorts = defaultdict(lambda: defaultdict(int))
        for user_id, data in user_cohorts.items():
            cohort_month = data["first_seen"].strftime("%Y-%m")
            for event_time in data["events"]:
                months_since = (event_time.year - data["first_seen"].year) * 12 + (
                    event_time.month - data["first_seen"].month
                )
                cohorts[cohort_month][months_since] += 1

        return {
            "cohort_matrix": {k: dict(v) for k, v in cohorts.items()},
            "total_cohorts": len(cohorts),
            "total_users": len(user_cohorts),
            "analysis_period": {"start": cohort_start.isoformat(), "end": cohort_end.isoformat()},
        }

    async def retention_analysis(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        retention_period_days: int = 30,
    ) -> dict[str, Any]:
        """
        Analyze user/patient retention.

        Feature #117: Retention analysis support
        """
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        # Track user activity
        user_activity = defaultdict(list)
        for event in events:
            user_id = event.payload.get("user_id") or event.payload.get("patient_id")
            if user_id:
                user_activity[user_id].append(event.event_timestamp)

        # Calculate retention
        retained_users = 0
        churned_users = 0
        cutoff_date = end_date - timedelta(days=retention_period_days)

        for user_id, timestamps in user_activity.items():
            last_activity = max(timestamps)
            if last_activity >= cutoff_date:
                retained_users += 1
            else:
                churned_users += 1

        total_users = len(user_activity)
        retention_rate = (retained_users / total_users * 100) if total_users > 0 else 0

        return {
            "total_users": total_users,
            "retained_users": retained_users,
            "churned_users": churned_users,
            "retention_rate": retention_rate,
            "churn_rate": 100 - retention_rate,
            "retention_period_days": retention_period_days,
        }

    async def conversion_analysis(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        conversion_event: str = "transport_complete",
    ) -> dict[str, Any]:
        """
        Analyze conversion rates through funnel.

        Feature #118: Conversion analysis support
        """
        # Query all events in period
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        # Build funnel stages
        funnel_stages = defaultdict(set)
        for event in events:
            call_id = event.payload.get("call_id") or event.payload.get("incident_id")
            if not call_id:
                continue

            event_type = event.event_type
            funnel_stages[event_type].add(call_id)

        # Calculate conversion rates
        total_starts = len(funnel_stages.get("dispatch", set()))
        conversions = len(funnel_stages.get(conversion_event, set()))
        conversion_rate = (conversions / total_starts * 100) if total_starts > 0 else 0

        return {
            "total_opportunities": total_starts,
            "conversions": conversions,
            "conversion_rate": conversion_rate,
            "funnel_stages": {stage: len(ids) for stage, ids in funnel_stages.items()},
            "drop_off_rate": 100 - conversion_rate,
        }

    async def payer_lifecycle_analysis(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Analyze payer lifecycle and relationship duration.

        Feature #119: Payer lifecycle analysis
        """
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain == "billing",
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        payer_activity = defaultdict(lambda: {"first_claim": None, "last_claim": None, "claim_count": 0})

        for event in events:
            payer_id = event.payload.get("payer_id")
            if not payer_id:
                continue

            claim_date = event.event_timestamp
            if payer_activity[payer_id]["first_claim"] is None or claim_date < payer_activity[payer_id]["first_claim"]:
                payer_activity[payer_id]["first_claim"] = claim_date
            if payer_activity[payer_id]["last_claim"] is None or claim_date > payer_activity[payer_id]["last_claim"]:
                payer_activity[payer_id]["last_claim"] = claim_date
            payer_activity[payer_id]["claim_count"] += 1

        # Calculate lifecycle metrics
        lifecycle_metrics = []
        for payer_id, data in payer_activity.items():
            if data["first_claim"] and data["last_claim"]:
                duration_days = (data["last_claim"] - data["first_claim"]).days
                lifecycle_metrics.append(
                    {
                        "payer_id": payer_id,
                        "duration_days": duration_days,
                        "claim_count": data["claim_count"],
                        "claims_per_month": data["claim_count"] / (duration_days / 30) if duration_days > 0 else 0,
                    }
                )

        avg_duration = sum(m["duration_days"] for m in lifecycle_metrics) / len(lifecycle_metrics) if lifecycle_metrics else 0

        return {
            "total_payers": len(payer_activity),
            "average_relationship_duration_days": avg_duration,
            "payer_metrics": lifecycle_metrics,
            "total_claims": sum(data["claim_count"] for data in payer_activity.values()),
        }

    async def recurring_patient_analysis(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        recurrence_threshold: int = 3,
    ) -> dict[str, Any]:
        """
        Analyze recurring patient patterns.

        Feature #120: Recurring patient analysis
        """
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain.in_(["cad", "epcr"]),
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        patient_visits = defaultdict(int)
        for event in events:
            patient_id = event.payload.get("patient_id")
            if patient_id:
                patient_visits[patient_id] += 1

        recurring_patients = {pid: count for pid, count in patient_visits.items() if count >= recurrence_threshold}

        return {
            "total_patients": len(patient_visits),
            "recurring_patients": len(recurring_patients),
            "recurring_rate": (len(recurring_patients) / len(patient_visits) * 100) if patient_visits else 0,
            "recurrence_threshold": recurrence_threshold,
            "most_frequent_patients": sorted(recurring_patients.items(), key=lambda x: x[1], reverse=True)[:10],
            "total_visits": sum(patient_visits.values()),
            "recurring_visits": sum(recurring_patients.values()),
        }

    async def no_show_pattern_analysis(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Analyze no-show and missed appointment patterns.

        Features #121-122: Missed-appointment analysis, no-show pattern analysis
        """
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.event_type.in_(["appointment_scheduled", "appointment_no_show", "appointment_cancelled"]),
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        scheduled = 0
        no_shows = 0
        cancellations = 0

        for event in events:
            if event.event_type == "appointment_scheduled":
                scheduled += 1
            elif event.event_type == "appointment_no_show":
                no_shows += 1
            elif event.event_type == "appointment_cancelled":
                cancellations += 1

        no_show_rate = (no_shows / scheduled * 100) if scheduled > 0 else 0
        cancellation_rate = (cancellations / scheduled * 100) if scheduled > 0 else 0

        return {
            "total_scheduled": scheduled,
            "no_shows": no_shows,
            "cancellations": cancellations,
            "completed": scheduled - no_shows - cancellations,
            "no_show_rate": no_show_rate,
            "cancellation_rate": cancellation_rate,
            "completion_rate": 100 - no_show_rate - cancellation_rate,
        }

    async def document_completion_lag_analysis(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any]:
        """
        Analyze document completion lag times.

        Features #123-125: Document completion, chart-signature, export-readiness lag analysis
        """
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain == "epcr",
            AnalyticsEvent.event_type.in_(["chart_created", "chart_completed", "chart_signed", "chart_exported"]),
            AnalyticsEvent.event_timestamp >= start_date,
            AnalyticsEvent.event_timestamp < end_date,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        # Group by chart_id
        chart_timelines = defaultdict(dict)
        for event in events:
            chart_id = event.payload.get("chart_id")
            if not chart_id:
                continue
            chart_timelines[chart_id][event.event_type] = event.event_timestamp

        # Calculate lag times
        completion_lags = []
        signature_lags = []
        export_lags = []

        for chart_id, timeline in chart_timelines.items():
            created = timeline.get("chart_created")
            completed = timeline.get("chart_completed")
            signed = timeline.get("chart_signed")
            exported = timeline.get("chart_exported")

            if created and completed:
                lag = (completed - created).total_seconds() / 3600  # hours
                completion_lags.append(lag)

            if created and signed:
                lag = (signed - created).total_seconds() / 3600
                signature_lags.append(lag)

            if created and exported:
                lag = (exported - created).total_seconds() / 3600
                export_lags.append(lag)

        return {
            "completion_lag": {
                "average_hours": sum(completion_lags) / len(completion_lags) if completion_lags else 0,
                "median_hours": sorted(completion_lags)[len(completion_lags) // 2] if completion_lags else 0,
                "max_hours": max(completion_lags) if completion_lags else 0,
                "within_24h_percentage": sum(1 for lag in completion_lags if lag <= 24)
                / len(completion_lags)
                * 100
                if completion_lags
                else 0,
            },
            "signature_lag": {
                "average_hours": sum(signature_lags) / len(signature_lags) if signature_lags else 0,
                "median_hours": sorted(signature_lags)[len(signature_lags) // 2] if signature_lags else 0,
            },
            "export_lag": {
                "average_hours": sum(export_lags) / len(export_lags) if export_lags else 0,
                "median_hours": sorted(export_lags)[len(export_lags) // 2] if export_lags else 0,
            },
            "total_charts_analyzed": len(chart_timelines),
        }


# Singleton instance
advanced_analytics_service = AdvancedAnalyticsService()
