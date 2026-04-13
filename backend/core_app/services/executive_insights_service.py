"""Executive insights service for high-level analytics and recommendations."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.models import AnalyticsEvent, KPIValue

logger = get_logger(__name__)


class ExecutiveInsightsService:
    """Service for generating executive-level insights and recommendations."""

    async def generate_executive_summary(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """
        Generate high-level executive summary.

        Feature #138: Executive summary generation
        """
        # Query key metrics
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.event_timestamp >= period_start,
            AnalyticsEvent.event_timestamp < period_end,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        # Calculate summary statistics
        total_events = len(events)
        domains = set(e.source_domain for e in events)
        event_types = set(e.event_type for e in events)

        # Domain breakdown
        domain_counts = defaultdict(int)
        for event in events:
            domain_counts[event.source_domain] += 1

        return {
            "summary_type": "executive",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_events": total_events,
            "active_domains": len(domains),
            "event_type_diversity": len(event_types),
            "domain_breakdown": dict(domain_counts),
            "top_domain": max(domain_counts.items(), key=lambda x: x[1])[0] if domain_counts else None,
        }

    async def generate_kpi_highlights(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
        top_n: int = 5,
    ) -> dict[str, Any]:
        """
        Highlight top performing and underperforming KPIs.

        Feature #139: KPI highlights report
        """
        # Query KPI values
        query = (
            select(KPIValue)
            .where(
                KPIValue.tenant_id == tenant_id,
                KPIValue.period_start >= period_start,
                KPIValue.period_end <= period_end,
            )
            .order_by(KPIValue.period_start.desc())
        )

        result = await db.execute(query)
        kpi_values = result.scalars().all()

        # Separate by status
        top_performers = []
        underperformers = []

        for kpi in kpi_values:
            kpi_data = {
                "kpi_code": kpi.kpi_code,
                "value": kpi.value,
                "status": kpi.status.value if kpi.status else "unknown",
                "delta_from_target": kpi.delta_from_target,
            }

            if kpi.status and kpi.status.value == "healthy":
                top_performers.append(kpi_data)
            elif kpi.status and kpi.status.value in ["warning", "critical"]:
                underperformers.append(kpi_data)

        # Sort and limit
        top_performers = sorted(top_performers, key=lambda x: x.get("delta_from_target", 0) or 0, reverse=True)[
            :top_n
        ]
        underperformers = sorted(underperformers, key=lambda x: x.get("delta_from_target", 0) or 0)[:top_n]

        return {
            "report_type": "kpi_highlights",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "top_performers": top_performers,
            "underperformers": underperformers,
            "total_kpis_analyzed": len(kpi_values),
        }

    async def generate_trend_alerts(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """
        Generate alerts for significant trends.

        Feature #140: Trend alert generation
        """
        # Query KPI values to identify trends
        query = (
            select(KPIValue)
            .where(
                KPIValue.tenant_id == tenant_id,
                KPIValue.period_start >= period_start,
                KPIValue.period_end <= period_end,
            )
            .order_by(KPIValue.kpi_code, KPIValue.period_start)
        )

        result = await db.execute(query)
        kpi_values = result.scalars().all()

        # Group by KPI code
        kpi_groups = defaultdict(list)
        for kpi in kpi_values:
            kpi_groups[kpi.kpi_code].append(kpi)

        # Identify significant trends
        alerts = []
        for kpi_code, values in kpi_groups.items():
            if len(values) < 2:
                continue

            # Check for consistent deterioration
            deteriorating = all(
                values[i].value > values[i + 1].value for i in range(len(values) - 1) if values[i].value is not None
            )

            # Check for consistent improvement
            improving = all(
                values[i].value < values[i + 1].value for i in range(len(values) - 1) if values[i].value is not None
            )

            if deteriorating:
                alerts.append(
                    {
                        "kpi_code": kpi_code,
                        "trend": "deteriorating",
                        "severity": "high",
                        "message": f"{kpi_code} showing consistent decline",
                        "data_points": len(values),
                    }
                )
            elif improving:
                alerts.append(
                    {
                        "kpi_code": kpi_code,
                        "trend": "improving",
                        "severity": "info",
                        "message": f"{kpi_code} showing consistent improvement",
                        "data_points": len(values),
                    }
                )

        return {
            "alert_type": "trend_alerts",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "alerts": alerts,
            "total_alerts": len(alerts),
        }

    async def generate_performance_recommendations(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """
        Generate actionable performance recommendations.

        Feature #141: Performance recommendation engine
        """
        # Query underperforming KPIs
        query = (
            select(KPIValue)
            .where(
                KPIValue.tenant_id == tenant_id,
                KPIValue.period_start >= period_start,
                KPIValue.period_end <= period_end,
                KPIValue.status.in_(["warning", "critical"]),
            )
            .order_by(KPIValue.period_start.desc())
        )

        result = await db.execute(query)
        underperforming_kpis = result.scalars().all()

        recommendations = []

        # Generate recommendations based on KPI codes
        for kpi in underperforming_kpis:
            if kpi.kpi_code == "response_time":
                recommendations.append(
                    {
                        "kpi_code": kpi.kpi_code,
                        "priority": "high",
                        "recommendation": "Review unit deployment and station coverage patterns",
                        "expected_impact": "Reduce response times by optimizing unit locations",
                    }
                )
            elif kpi.kpi_code == "chart_completion":
                recommendations.append(
                    {
                        "kpi_code": kpi.kpi_code,
                        "priority": "high",
                        "recommendation": "Implement crew reminders and completion workflows",
                        "expected_impact": "Improve documentation completion rates",
                    }
                )
            elif kpi.kpi_code == "denial_rate":
                recommendations.append(
                    {
                        "kpi_code": kpi.kpi_code,
                        "priority": "critical",
                        "recommendation": "Review billing documentation quality and submission timing",
                        "expected_impact": "Reduce claim denials and improve revenue",
                    }
                )
            elif kpi.kpi_code == "unit_utilization":
                recommendations.append(
                    {
                        "kpi_code": kpi.kpi_code,
                        "priority": "medium",
                        "recommendation": "Analyze staffing levels and adjust deployment strategy",
                        "expected_impact": "Optimize resource utilization",
                    }
                )
            else:
                recommendations.append(
                    {
                        "kpi_code": kpi.kpi_code,
                        "priority": "medium",
                        "recommendation": f"Review {kpi.kpi_code} performance and identify root causes",
                        "expected_impact": "Improve overall operational efficiency",
                    }
                )

        return {
            "recommendation_type": "performance",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
        }

    async def generate_cost_optimization_insights(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """
        Generate cost optimization insights.

        Feature #142: Cost-optimization insight generation
        """
        # Query billing and utilization data
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain.in_(["billing", "cad"]),
            AnalyticsEvent.event_timestamp >= period_start,
            AnalyticsEvent.event_timestamp < period_end,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        # Analyze utilization
        unit_events = [e for e in events if e.source_domain == "cad"]
        billing_events = [e for e in events if e.source_domain == "billing"]

        insights = []

        # Unit utilization insight
        if unit_events:
            unique_units = set()
            for event in unit_events:
                unit_id = event.payload.get("unit_id")
                if unit_id:
                    unique_units.add(unit_id)

            avg_events_per_unit = len(unit_events) / len(unique_units) if unique_units else 0

            if avg_events_per_unit < 10:
                insights.append(
                    {
                        "category": "utilization",
                        "finding": "Low unit utilization detected",
                        "recommendation": "Consider fleet right-sizing or deployment optimization",
                        "potential_savings": "Medium",
                    }
                )

        # Billing efficiency insight
        if billing_events:
            denied_claims = [e for e in billing_events if e.event_type == "claim_denied"]
            denial_rate = len(denied_claims) / len(billing_events) * 100 if billing_events else 0

            if denial_rate > 10:
                insights.append(
                    {
                        "category": "billing",
                        "finding": f"High denial rate: {denial_rate:.1f}%",
                        "recommendation": "Improve documentation quality and pre-submission validation",
                        "potential_savings": "High",
                    }
                )

        return {
            "insight_type": "cost_optimization",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "insights": insights,
            "total_insights": len(insights),
        }

    async def generate_quality_improvement_insights(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """
        Generate quality improvement insights.

        Feature #143: Quality-improvement insight generation
        """
        # Query ePCR and quality-related events
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain == "epcr",
            AnalyticsEvent.event_timestamp >= period_start,
            AnalyticsEvent.event_timestamp < period_end,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        insights = []

        # Analyze chart completion
        chart_created = [e for e in events if e.event_type == "chart_created"]
        chart_completed = [e for e in events if e.event_type == "chart_completed"]
        chart_signed = [e for e in events if e.event_type == "chart_signed"]

        completion_rate = len(chart_completed) / len(chart_created) * 100 if chart_created else 0
        signature_rate = len(chart_signed) / len(chart_created) * 100 if chart_created else 0

        if completion_rate < 90:
            insights.append(
                {
                    "category": "documentation",
                    "finding": f"Chart completion rate: {completion_rate:.1f}%",
                    "recommendation": "Implement automated reminders and workflow improvements",
                    "impact": "High",
                }
            )

        if signature_rate < 85:
            insights.append(
                {
                    "category": "documentation",
                    "finding": f"Chart signature rate: {signature_rate:.1f}%",
                    "recommendation": "Streamline signature workflow and add automated notifications",
                    "impact": "High",
                }
            )

        return {
            "insight_type": "quality_improvement",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "insights": insights,
            "total_insights": len(insights),
        }

    async def generate_capacity_planning_insights(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """
        Generate capacity planning insights.

        Feature #144: Capacity-planning insight generation
        """
        # Query operational events
        query = select(AnalyticsEvent).where(
            AnalyticsEvent.tenant_id == tenant_id,
            AnalyticsEvent.source_domain == "cad",
            AnalyticsEvent.event_timestamp >= period_start,
            AnalyticsEvent.event_timestamp < period_end,
        )

        result = await db.execute(query)
        events = result.scalars().all()

        # Analyze by hour of day
        hourly_distribution = defaultdict(int)
        for event in events:
            hour = event.event_timestamp.hour
            hourly_distribution[hour] += 1

        # Identify peak hours
        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0] if hourly_distribution else 0
        peak_volume = hourly_distribution[peak_hour] if hourly_distribution else 0

        # Calculate capacity recommendations
        avg_hourly = sum(hourly_distribution.values()) / 24 if hourly_distribution else 0

        insights = []

        if peak_volume > avg_hourly * 1.5:
            insights.append(
                {
                    "category": "capacity",
                    "finding": f"Peak hour ({peak_hour}:00) has {peak_volume} events vs avg {avg_hourly:.0f}",
                    "recommendation": "Add staffing during peak hours (adjust shift schedules)",
                    "impact": "High",
                }
            )

        return {
            "insight_type": "capacity_planning",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "insights": insights,
            "peak_hour": peak_hour,
            "peak_volume": peak_volume,
            "average_hourly": avg_hourly,
        }

    async def generate_risk_assessment(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> dict[str, Any]:
        """
        Generate risk assessment insights.

        Feature #145: Risk-assessment insight generation
        """
        # Query critical KPIs
        query = (
            select(KPIValue)
            .where(
                KPIValue.tenant_id == tenant_id,
                KPIValue.period_start >= period_start,
                KPIValue.period_end <= period_end,
                KPIValue.status == "critical",
            )
            .order_by(KPIValue.period_start.desc())
        )

        result = await db.execute(query)
        critical_kpis = result.scalars().all()

        risks = []

        for kpi in critical_kpis:
            risk_level = "high" if kpi.status.value == "critical" else "medium"

            risks.append(
                {
                    "kpi_code": kpi.kpi_code,
                    "risk_level": risk_level,
                    "current_value": kpi.value,
                    "threshold": kpi.threshold_critical,
                    "risk_description": f"{kpi.kpi_code} in critical state",
                    "mitigation_required": True,
                }
            )

        return {
            "assessment_type": "risk",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "risks": risks,
            "total_risks": len(risks),
            "overall_risk_level": "high" if len(risks) > 3 else "medium" if len(risks) > 0 else "low",
        }

    async def generate_top_action_items(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        Generate prioritized action items.

        Feature #146: Top action-item report
        """
        # Get recommendations and risks
        recommendations = await self.generate_performance_recommendations(db, tenant_id, period_start, period_end)
        risks = await self.generate_risk_assessment(db, tenant_id, period_start, period_end)

        action_items = []

        # Add critical risks as high-priority actions
        for risk in risks.get("risks", []):
            if risk["risk_level"] == "high":
                action_items.append(
                    {
                        "priority": 1,
                        "type": "risk_mitigation",
                        "title": f"Address critical {risk['kpi_code']}",
                        "description": risk["risk_description"],
                        "urgency": "immediate",
                    }
                )

        # Add high-priority recommendations
        for rec in recommendations.get("recommendations", []):
            if rec["priority"] == "critical":
                priority = 1
            elif rec["priority"] == "high":
                priority = 2
            else:
                priority = 3

            action_items.append(
                {
                    "priority": priority,
                    "type": "performance_improvement",
                    "title": f"Improve {rec['kpi_code']}",
                    "description": rec["recommendation"],
                    "urgency": "high" if priority <= 2 else "medium",
                }
            )

        # Sort by priority and limit
        action_items = sorted(action_items, key=lambda x: x["priority"])[:limit]

        return {
            "report_type": "action_items",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "action_items": action_items,
            "total_items": len(action_items),
        }

    async def generate_monthly_executive_brief(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        month: datetime,
    ) -> dict[str, Any]:
        """
        Generate comprehensive monthly executive brief.

        Feature #147: Monthly executive brief
        """
        # Calculate period
        period_start = month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period_start.month == 12:
            period_end = period_start.replace(year=period_start.year + 1, month=1)
        else:
            period_end = period_start.replace(month=period_start.month + 1)

        # Gather all insights
        summary = await self.generate_executive_summary(db, tenant_id, period_start, period_end)
        highlights = await self.generate_kpi_highlights(db, tenant_id, period_start, period_end)
        trends = await self.generate_trend_alerts(db, tenant_id, period_start, period_end)
        actions = await self.generate_top_action_items(db, tenant_id, period_start, period_end, limit=5)

        return {
            "brief_type": "monthly_executive",
            "period": month.strftime("%Y-%m"),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "summary": summary,
            "kpi_highlights": highlights,
            "trend_alerts": trends,
            "top_actions": actions,
        }

    async def generate_quarterly_review(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        quarter: int,
        year: int,
    ) -> dict[str, Any]:
        """
        Generate quarterly business review.

        Feature #148: Quarterly review report
        """
        # Calculate quarter dates
        quarter_start_month = (quarter - 1) * 3 + 1
        period_start = datetime(year, quarter_start_month, 1)

        if quarter == 4:
            period_end = datetime(year + 1, 1, 1)
        else:
            period_end = datetime(year, quarter_start_month + 3, 1)

        # Gather comprehensive insights
        summary = await self.generate_executive_summary(db, tenant_id, period_start, period_end)
        cost_insights = await self.generate_cost_optimization_insights(db, tenant_id, period_start, period_end)
        quality_insights = await self.generate_quality_improvement_insights(db, tenant_id, period_start, period_end)
        capacity_insights = await self.generate_capacity_planning_insights(db, tenant_id, period_start, period_end)

        return {
            "review_type": "quarterly",
            "quarter": f"Q{quarter} {year}",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "executive_summary": summary,
            "cost_optimization": cost_insights,
            "quality_improvement": quality_insights,
            "capacity_planning": capacity_insights,
        }

    async def generate_annual_report(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        year: int,
    ) -> dict[str, Any]:
        """
        Generate annual performance report.

        Feature #149: Annual report generation
        """
        period_start = datetime(year, 1, 1)
        period_end = datetime(year + 1, 1, 1)

        # Gather yearly insights
        summary = await self.generate_executive_summary(db, tenant_id, period_start, period_end)
        highlights = await self.generate_kpi_highlights(db, tenant_id, period_start, period_end, top_n=10)
        recommendations = await self.generate_performance_recommendations(db, tenant_id, period_start, period_end)

        return {
            "report_type": "annual",
            "year": year,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "annual_summary": summary,
            "year_highlights": highlights,
            "strategic_recommendations": recommendations,
        }

    async def generate_custom_insights(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        period_start: datetime,
        period_end: datetime,
        focus_areas: list[str],
    ) -> dict[str, Any]:
        """
        Generate custom insights based on focus areas.

        Features #150-154: Custom insights for specific focus areas
        """
        insights = {}

        if "cost" in focus_areas:
            insights["cost_optimization"] = await self.generate_cost_optimization_insights(
                db, tenant_id, period_start, period_end
            )

        if "quality" in focus_areas:
            insights["quality_improvement"] = await self.generate_quality_improvement_insights(
                db, tenant_id, period_start, period_end
            )

        if "capacity" in focus_areas:
            insights["capacity_planning"] = await self.generate_capacity_planning_insights(
                db, tenant_id, period_start, period_end
            )

        if "risk" in focus_areas:
            insights["risk_assessment"] = await self.generate_risk_assessment(db, tenant_id, period_start, period_end)

        if "performance" in focus_areas:
            insights["performance_recommendations"] = await self.generate_performance_recommendations(
                db, tenant_id, period_start, period_end
            )

        return {
            "insight_type": "custom",
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "focus_areas": focus_areas,
            "insights": insights,
        }


# Singleton instance
executive_insights_service = ExecutiveInsightsService()
