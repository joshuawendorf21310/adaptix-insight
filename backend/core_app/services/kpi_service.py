"""KPI calculation and management service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.models import KPIDefinition, KPIValue
from core_app.schemas import AggregationLevelEnum, KPIStatus, KPIValueSchema, TrendDirection

logger = get_logger(__name__)


class KPIService:
    """Service for KPI definition and calculation."""

    async def get_kpi_definition(self, db: AsyncSession, kpi_code: str) -> KPIDefinition | None:
        """Get KPI definition by code."""
        result = await db.execute(select(KPIDefinition).where(KPIDefinition.kpi_code == kpi_code))
        return result.scalar_one_or_none()

    async def calculate_kpi_status(
        self,
        value: float,
        threshold_warning: float | None,
        threshold_critical: float | None,
    ) -> KPIStatus:
        """
        Calculate KPI status based on thresholds.

        Feature #37: KPI status classification
        """
        if threshold_critical is not None and value >= threshold_critical:
            return KPIStatus.CRITICAL
        if threshold_warning is not None and value >= threshold_warning:
            return KPIStatus.WARNING
        return KPIStatus.HEALTHY

    async def calculate_trend_direction(
        self,
        current_value: float,
        previous_value: float | None,
        threshold: float = 0.05,
    ) -> TrendDirection:
        """
        Calculate trend direction.

        Feature #40: KPI trend direction classification
        """
        if previous_value is None:
            return TrendDirection.STABLE

        change_pct = (current_value - previous_value) / previous_value if previous_value != 0 else 0

        if abs(change_pct) < threshold:
            return TrendDirection.STABLE
        elif change_pct > 0:
            return TrendDirection.UP
        else:
            return TrendDirection.DOWN

    async def store_kpi_value(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        kpi_code: str,
        aggregation_level: AggregationLevelEnum,
        period_start: datetime,
        period_end: datetime,
        value: float,
        status: KPIStatus | None = None,
        trend_direction: TrendDirection | None = None,
        delta_from_previous: float | None = None,
        delta_from_target: float | None = None,
        metadata: dict | None = None,
        quality_score: float | None = None,
    ) -> KPIValue:
        """Store calculated KPI value."""
        kpi_value = KPIValue(
            tenant_id=tenant_id,
            kpi_code=kpi_code,
            aggregation_level=aggregation_level.value,
            period_start=period_start,
            period_end=period_end,
            value=value,
            status=status.value if status else None,
            trend_direction=trend_direction.value if trend_direction else None,
            delta_from_previous=delta_from_previous,
            delta_from_target=delta_from_target,
            metadata=metadata,
            quality_score=quality_score,
        )
        db.add(kpi_value)
        await db.flush()
        return kpi_value

    async def get_kpi_values(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        kpi_codes: list[str] | None,
        aggregation_level: AggregationLevelEnum,
        period_start: datetime,
        period_end: datetime,
    ) -> list[KPIValueSchema]:
        """Get KPI values for a time period."""
        query = select(KPIValue).where(
            KPIValue.tenant_id == tenant_id,
            KPIValue.aggregation_level == aggregation_level.value,
            KPIValue.period_start >= period_start,
            KPIValue.period_end <= period_end,
        )

        if kpi_codes:
            query = query.where(KPIValue.kpi_code.in_(kpi_codes))

        result = await db.execute(query)
        kpi_values = result.scalars().all()

        # Convert to schemas
        schemas = []
        for kv in kpi_values:
            schemas.append(
                KPIValueSchema(
                    id=kv.id,
                    tenant_id=kv.tenant_id,
                    kpi_code=kv.kpi_code,
                    aggregation_level=AggregationLevelEnum(kv.aggregation_level),
                    period_start=kv.period_start,
                    period_end=kv.period_end,
                    value=kv.value,
                    status=KPIStatus(kv.status) if kv.status else None,
                    trend_direction=TrendDirection(kv.trend_direction) if kv.trend_direction else None,
                    delta_from_previous=kv.delta_from_previous,
                    delta_from_target=kv.delta_from_target,
                    quality_score=kv.quality_score,
                )
            )

        return schemas

    async def seed_kpi_definitions(self, db: AsyncSession) -> None:
        """
        Seed core KPI definitions.

        Features #31-59: KPI definitions for operational metrics
        """
        kpi_definitions = [
            # Operational KPIs
            {
                "kpi_code": "response_time",
                "kpi_name": "Response Time",
                "description": "Average time from dispatch to on-scene arrival",
                "formula": "AVG(scene_arrival_timestamp - dispatch_timestamp)",
                "source_domains": ["cad", "epcr"],
                "unit": "minutes",
                "threshold_warning": 10.0,
                "threshold_critical": 15.0,
                "target_value": 8.0,
                "owner": "operations",
            },
            {
                "kpi_code": "turnout_time",
                "kpi_name": "Turnout Time",
                "description": "Time from dispatch to unit en route",
                "formula": "AVG(enroute_timestamp - dispatch_timestamp)",
                "source_domains": ["cad"],
                "unit": "minutes",
                "threshold_warning": 2.0,
                "threshold_critical": 3.0,
                "target_value": 1.5,
                "owner": "operations",
            },
            {
                "kpi_code": "scene_time",
                "kpi_name": "Scene Time",
                "description": "Time spent on scene",
                "formula": "AVG(depart_scene_timestamp - scene_arrival_timestamp)",
                "source_domains": ["cad", "epcr"],
                "unit": "minutes",
                "owner": "operations",
            },
            {
                "kpi_code": "transport_time",
                "kpi_name": "Transport Time",
                "description": "Time from scene departure to hospital arrival",
                "formula": "AVG(hospital_arrival_timestamp - depart_scene_timestamp)",
                "source_domains": ["cad", "epcr"],
                "unit": "minutes",
                "owner": "operations",
            },
            {
                "kpi_code": "chart_completion",
                "kpi_name": "Chart Completion Rate",
                "description": "Percentage of charts completed within 24 hours",
                "formula": "COUNT(completed_within_24h) / COUNT(total_charts) * 100",
                "source_domains": ["epcr"],
                "unit": "percent",
                "threshold_warning": 85.0,
                "threshold_critical": 75.0,
                "target_value": 95.0,
                "owner": "documentation",
            },
            {
                "kpi_code": "nemsis_readiness",
                "kpi_name": "NEMSIS Readiness",
                "description": "Percentage of charts NEMSIS-compliant",
                "formula": "COUNT(nemsis_compliant) / COUNT(total_charts) * 100",
                "source_domains": ["epcr"],
                "unit": "percent",
                "threshold_warning": 90.0,
                "threshold_critical": 85.0,
                "target_value": 98.0,
                "owner": "compliance",
            },
            {
                "kpi_code": "billing_throughput",
                "kpi_name": "Billing Throughput",
                "description": "Average days from service to claim submission",
                "formula": "AVG(claim_submission_date - service_date)",
                "source_domains": ["billing"],
                "unit": "days",
                "threshold_warning": 5.0,
                "threshold_critical": 7.0,
                "target_value": 3.0,
                "owner": "billing",
            },
            {
                "kpi_code": "denial_rate",
                "kpi_name": "Claim Denial Rate",
                "description": "Percentage of claims denied",
                "formula": "COUNT(denied_claims) / COUNT(total_claims) * 100",
                "source_domains": ["billing"],
                "unit": "percent",
                "threshold_warning": 10.0,
                "threshold_critical": 15.0,
                "target_value": 5.0,
                "owner": "billing",
            },
            {
                "kpi_code": "staffing_coverage",
                "kpi_name": "Staffing Coverage",
                "description": "Percentage of shifts fully staffed",
                "formula": "COUNT(fully_staffed_shifts) / COUNT(total_shifts) * 100",
                "source_domains": ["workforce", "crewlink"],
                "unit": "percent",
                "threshold_warning": 85.0,
                "threshold_critical": 75.0,
                "target_value": 95.0,
                "owner": "workforce",
            },
            {
                "kpi_code": "fatigue_risk",
                "kpi_name": "Fatigue Risk Score",
                "description": "Crew fatigue risk assessment score",
                "formula": "AVG(consecutive_hours_worked / max_safe_hours)",
                "source_domains": ["workforce", "crewlink"],
                "unit": "score",
                "threshold_warning": 0.7,
                "threshold_critical": 0.85,
                "target_value": 0.5,
                "owner": "workforce",
            },
            {
                "kpi_code": "unit_utilization",
                "kpi_name": "Unit Utilization",
                "description": "Percentage of time units are in service",
                "formula": "SUM(in_service_time) / SUM(available_time) * 100",
                "source_domains": ["cad", "field"],
                "unit": "percent",
                "owner": "operations",
            },
            {
                "kpi_code": "ai_usage",
                "kpi_name": "AI Feature Usage",
                "description": "AI feature adoption rate",
                "formula": "COUNT(ai_feature_uses) / COUNT(eligible_interactions) * 100",
                "source_domains": ["ai", "command"],
                "unit": "percent",
                "owner": "product",
            },
            {
                "kpi_code": "roi_realization",
                "kpi_name": "ROI Realization",
                "description": "Realized ROI from platform adoption",
                "formula": "(benefits - costs) / costs * 100",
                "source_domains": ["billing", "workforce", "insight"],
                "unit": "percent",
                "target_value": 200.0,
                "owner": "executive",
            },
            # Additional KPIs (Features 52-54, 57-59)
            {
                "kpi_code": "apparatus_utilization",
                "kpi_name": "Apparatus Utilization",
                "description": "Percentage of apparatus fleet in active use",
                "formula": "COUNT(active_apparatus) / COUNT(total_apparatus) * 100",
                "source_domains": ["cad", "fleet"],
                "unit": "percent",
                "threshold_warning": 60.0,
                "threshold_critical": 40.0,
                "target_value": 75.0,
                "owner": "operations",
            },
            {
                "kpi_code": "recurring_transport",
                "kpi_name": "Recurring Transport Rate",
                "description": "Rate of patients requiring multiple transports",
                "formula": "COUNT(patients_with_multiple_transports) / COUNT(unique_patients) * 100",
                "source_domains": ["epcr", "cad"],
                "unit": "percent",
                "owner": "clinical",
            },
            {
                "kpi_code": "investor_funnel",
                "kpi_name": "Investor Funnel Conversion",
                "description": "Investor pipeline conversion rate",
                "formula": "COUNT(converted_investors) / COUNT(total_prospects) * 100",
                "source_domains": ["commercial", "insight"],
                "unit": "percent",
                "target_value": 15.0,
                "owner": "commercial",
            },
            {
                "kpi_code": "ai_cost",
                "kpi_name": "AI Cost per Transaction",
                "description": "Average AI infrastructure cost per transaction",
                "formula": "SUM(ai_costs) / COUNT(ai_transactions)",
                "source_domains": ["ai", "command"],
                "unit": "dollars",
                "threshold_warning": 0.50,
                "threshold_critical": 1.00,
                "target_value": 0.25,
                "owner": "product",
            },
            {
                "kpi_code": "patient_portal_usage",
                "kpi_name": "Patient Portal Usage",
                "description": "Patient portal active user rate",
                "formula": "COUNT(active_portal_users) / COUNT(eligible_patients) * 100",
                "source_domains": ["patient_portal", "epcr"],
                "unit": "percent",
                "target_value": 40.0,
                "owner": "product",
            },
            {
                "kpi_code": "trust_compliance",
                "kpi_name": "Trust & Compliance Score",
                "description": "Overall trust and regulatory compliance score",
                "formula": "WEIGHTED_AVG(compliance_checks_passed)",
                "source_domains": ["compliance", "audit"],
                "unit": "score",
                "threshold_warning": 85.0,
                "threshold_critical": 70.0,
                "target_value": 95.0,
                "owner": "compliance",
            },
        ]

        for kpi_def in kpi_definitions:
            # Check if exists
            existing = await db.execute(
                select(KPIDefinition).where(KPIDefinition.kpi_code == kpi_def["kpi_code"])
            )
            if not existing.scalar_one_or_none():
                db.add(KPIDefinition(**kpi_def))

        await db.flush()
        logger.info("kpi_definitions_seeded", count=len(kpi_definitions))


# Singleton instance
kpi_service = KPIService()
