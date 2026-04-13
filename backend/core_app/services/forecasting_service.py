"""Forecasting service for predictive analytics."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.models import AnalyticsEvent, KPIValue

logger = get_logger(__name__)


class ForecastingService:
    """Service for time-series forecasting and predictive analytics."""

    async def prepare_forecasting_input(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        metric_name: str,
        start_date: datetime,
        end_date: datetime,
        aggregation_interval: str = "daily",
    ) -> dict[str, Any]:
        """
        Prepare time-series data for forecasting.

        Feature #126: Forecasting input pipeline
        """
        # Query historical data
        if aggregation_interval == "daily":
            time_unit = func.date(AnalyticsEvent.event_timestamp)
        elif aggregation_interval == "hourly":
            time_unit = func.date_trunc("hour", AnalyticsEvent.event_timestamp)
        else:
            time_unit = func.date(AnalyticsEvent.event_timestamp)

        query = (
            select(
                time_unit.label("time_bucket"),
                func.count(AnalyticsEvent.id).label("value"),
            )
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp < end_date,
            )
            .group_by(time_unit)
            .order_by(time_unit)
        )

        result = await db.execute(query)
        rows = result.all()

        # Convert to time series
        time_series = []
        for row in rows:
            time_series.append({"timestamp": row.time_bucket, "value": float(row.value)})

        # Calculate basic statistics
        values = [point["value"] for point in time_series]
        mean_value = np.mean(values) if values else 0
        std_value = np.std(values) if values else 0
        trend = self._calculate_trend(values)

        return {
            "metric_name": metric_name,
            "time_series": time_series,
            "data_points": len(time_series),
            "mean": mean_value,
            "std_dev": std_value,
            "trend": trend,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "aggregation_interval": aggregation_interval,
        }

    def _calculate_trend(self, values: list[float]) -> str:
        """Calculate trend direction from values."""
        if len(values) < 2:
            return "insufficient_data"

        # Simple linear regression slope
        x = np.arange(len(values))
        y = np.array(values)
        slope = np.polyfit(x, y, 1)[0]

        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"

    async def forecast_call_volume(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        forecast_periods: int = 30,
    ) -> dict[str, Any]:
        """
        Forecast future call/incident volume.

        Feature #127: Volume forecast support
        """
        # Get historical data
        input_data = await self.prepare_forecasting_input(
            db=db,
            tenant_id=tenant_id,
            metric_name="call_volume",
            start_date=start_date,
            end_date=end_date,
            aggregation_interval="daily",
        )

        values = [point["value"] for point in input_data["time_series"]]

        # Simple exponential smoothing forecast
        forecast = self._exponential_smoothing_forecast(values, forecast_periods, alpha=0.3)

        return {
            "metric_name": "call_volume",
            "historical_periods": len(values),
            "forecast_periods": forecast_periods,
            "forecast_values": forecast,
            "mean_forecast": np.mean(forecast),
            "trend": input_data["trend"],
            "model_type": "exponential_smoothing",
        }

    async def forecast_staffing_needs(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        forecast_periods: int = 30,
    ) -> dict[str, Any]:
        """
        Forecast staffing requirements.

        Feature #128: Staffing forecast support
        """
        # Query staffing events
        query = (
            select(
                func.date(AnalyticsEvent.event_timestamp).label("date"),
                func.count(func.distinct(AnalyticsEvent.payload["crew_id"].astext)).label("crew_count"),
            )
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.source_domain == "cad",
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp < end_date,
            )
            .group_by(func.date(AnalyticsEvent.event_timestamp))
            .order_by(func.date(AnalyticsEvent.event_timestamp))
        )

        result = await db.execute(query)
        rows = result.all()

        staffing_levels = [float(row.crew_count) for row in rows]

        # Forecast future staffing needs
        forecast = self._exponential_smoothing_forecast(staffing_levels, forecast_periods, alpha=0.2)

        return {
            "metric_name": "staffing_needs",
            "historical_periods": len(staffing_levels),
            "forecast_periods": forecast_periods,
            "forecast_values": forecast,
            "recommended_min_staff": int(np.min(forecast)),
            "recommended_max_staff": int(np.max(forecast)),
            "recommended_avg_staff": int(np.mean(forecast)),
            "model_type": "exponential_smoothing",
        }

    async def forecast_transport_demand(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        forecast_periods: int = 30,
    ) -> dict[str, Any]:
        """
        Forecast transport demand patterns.

        Feature #129: Transport demand forecast
        """
        # Query transport events
        query = (
            select(
                func.date(AnalyticsEvent.event_timestamp).label("date"),
                func.count(AnalyticsEvent.id).label("transport_count"),
            )
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.event_type.in_(["transport_initiated", "transport_complete"]),
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp < end_date,
            )
            .group_by(func.date(AnalyticsEvent.event_timestamp))
            .order_by(func.date(AnalyticsEvent.event_timestamp))
        )

        result = await db.execute(query)
        rows = result.all()

        transport_counts = [float(row.transport_count) for row in rows]

        # Forecast transport demand
        forecast = self._exponential_smoothing_forecast(transport_counts, forecast_periods, alpha=0.25)

        return {
            "metric_name": "transport_demand",
            "historical_periods": len(transport_counts),
            "forecast_periods": forecast_periods,
            "forecast_values": forecast,
            "expected_daily_transports": int(np.mean(forecast)),
            "peak_demand_day": int(np.max(forecast)),
            "model_type": "exponential_smoothing",
        }

    async def forecast_denial_risk(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        forecast_periods: int = 30,
    ) -> dict[str, Any]:
        """
        Forecast billing denial risk.

        Feature #130: Denial-risk forecast
        """
        # Query denial events
        query = (
            select(
                func.date(AnalyticsEvent.event_timestamp).label("date"),
                func.count(AnalyticsEvent.id).label("denial_count"),
            )
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.source_domain == "billing",
                AnalyticsEvent.event_type == "claim_denied",
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp < end_date,
            )
            .group_by(func.date(AnalyticsEvent.event_timestamp))
            .order_by(func.date(AnalyticsEvent.event_timestamp))
        )

        result = await db.execute(query)
        rows = result.all()

        denial_counts = [float(row.denial_count) for row in rows]

        if not denial_counts:
            denial_counts = [0.0]

        # Forecast denials
        forecast = self._exponential_smoothing_forecast(denial_counts, forecast_periods, alpha=0.3)

        # Calculate risk level
        avg_forecast = np.mean(forecast)
        historical_avg = np.mean(denial_counts)
        risk_increase = (avg_forecast - historical_avg) / historical_avg * 100 if historical_avg > 0 else 0

        if risk_increase > 20:
            risk_level = "high"
        elif risk_increase > 10:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "metric_name": "denial_risk",
            "historical_periods": len(denial_counts),
            "forecast_periods": forecast_periods,
            "forecast_values": forecast,
            "expected_daily_denials": avg_forecast,
            "risk_level": risk_level,
            "risk_increase_pct": risk_increase,
            "model_type": "exponential_smoothing",
        }

    async def forecast_budget_impact(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        forecast_periods: int = 90,
    ) -> dict[str, Any]:
        """
        Forecast budget and revenue impact.

        Feature #131: Budget-impact forecast
        """
        # Query revenue events
        query = (
            select(
                func.date(AnalyticsEvent.event_timestamp).label("date"),
                func.sum(
                    func.cast(AnalyticsEvent.payload["amount"].astext, func.numeric())
                ).label("revenue"),
            )
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.source_domain == "billing",
                AnalyticsEvent.event_type.in_(["claim_paid", "payment_received"]),
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp < end_date,
            )
            .group_by(func.date(AnalyticsEvent.event_timestamp))
            .order_by(func.date(AnalyticsEvent.event_timestamp))
        )

        result = await db.execute(query)
        rows = result.all()

        revenue_values = [float(row.revenue) if row.revenue else 0.0 for row in rows]

        if not revenue_values:
            revenue_values = [0.0]

        # Forecast revenue
        forecast = self._exponential_smoothing_forecast(revenue_values, forecast_periods, alpha=0.2)

        total_forecast = sum(forecast)
        monthly_avg = total_forecast / (forecast_periods / 30) if forecast_periods >= 30 else total_forecast

        return {
            "metric_name": "budget_impact",
            "historical_periods": len(revenue_values),
            "forecast_periods": forecast_periods,
            "forecast_values": forecast,
            "total_forecast_revenue": total_forecast,
            "monthly_avg_revenue": monthly_avg,
            "model_type": "exponential_smoothing",
        }

    async def forecast_unit_utilization(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        forecast_periods: int = 30,
    ) -> dict[str, Any]:
        """
        Forecast unit/vehicle utilization rates.

        Feature #132: Utilization forecast
        """
        # Query unit activity
        query = (
            select(
                func.date(AnalyticsEvent.event_timestamp).label("date"),
                func.count(func.distinct(AnalyticsEvent.payload["unit_id"].astext)).label("active_units"),
            )
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.source_domain == "cad",
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp < end_date,
            )
            .group_by(func.date(AnalyticsEvent.event_timestamp))
            .order_by(func.date(AnalyticsEvent.event_timestamp))
        )

        result = await db.execute(query)
        rows = result.all()

        utilization_values = [float(row.active_units) for row in rows]

        # Forecast utilization
        forecast = self._exponential_smoothing_forecast(utilization_values, forecast_periods, alpha=0.25)

        return {
            "metric_name": "unit_utilization",
            "historical_periods": len(utilization_values),
            "forecast_periods": forecast_periods,
            "forecast_values": forecast,
            "avg_daily_units_needed": int(np.mean(forecast)),
            "peak_units_needed": int(np.max(forecast)),
            "model_type": "exponential_smoothing",
        }

    async def forecast_capacity_needs(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime,
        forecast_periods: int = 30,
    ) -> dict[str, Any]:
        """
        Forecast capacity and resource requirements.

        Feature #133: Capacity forecast
        """
        # Query capacity metrics
        query = (
            select(
                func.date(AnalyticsEvent.event_timestamp).label("date"),
                func.count(AnalyticsEvent.id).label("event_count"),
            )
            .where(
                AnalyticsEvent.tenant_id == tenant_id,
                AnalyticsEvent.event_timestamp >= start_date,
                AnalyticsEvent.event_timestamp < end_date,
            )
            .group_by(func.date(AnalyticsEvent.event_timestamp))
            .order_by(func.date(AnalyticsEvent.event_timestamp))
        )

        result = await db.execute(query)
        rows = result.all()

        capacity_values = [float(row.event_count) for row in rows]

        # Forecast capacity needs
        forecast = self._exponential_smoothing_forecast(capacity_values, forecast_periods, alpha=0.3)

        # Determine capacity recommendations
        avg_forecast = np.mean(forecast)
        max_forecast = np.max(forecast)

        return {
            "metric_name": "capacity_needs",
            "historical_periods": len(capacity_values),
            "forecast_periods": forecast_periods,
            "forecast_values": forecast,
            "recommended_avg_capacity": avg_forecast,
            "recommended_peak_capacity": max_forecast,
            "capacity_buffer_recommendation": max_forecast * 1.2,  # 20% buffer
            "model_type": "exponential_smoothing",
        }

    async def add_confidence_bands(
        self,
        forecast_result: dict[str, Any],
        confidence_level: float = 0.95,
    ) -> dict[str, Any]:
        """
        Add confidence intervals to forecast.

        Feature #134: Confidence-band support
        """
        forecast_values = forecast_result["forecast_values"]

        # Calculate standard error (simplified approach)
        std_error = np.std(forecast_values) * 1.5

        # Calculate confidence bands
        z_score = 1.96 if confidence_level == 0.95 else 2.576  # 95% or 99%

        upper_band = [val + (z_score * std_error) for val in forecast_values]
        lower_band = [max(0, val - (z_score * std_error)) for val in forecast_values]  # No negative values

        forecast_result["confidence_bands"] = {
            "confidence_level": confidence_level,
            "upper_band": upper_band,
            "lower_band": lower_band,
            "std_error": std_error,
        }

        return forecast_result

    async def generate_best_case_scenario(
        self,
        forecast_result: dict[str, Any],
        improvement_factor: float = 0.15,
    ) -> dict[str, Any]:
        """
        Generate best-case scenario forecast.

        Feature #135: Best-case scenario modeling
        """
        forecast_values = forecast_result["forecast_values"]

        # Best case: improve by improvement_factor
        best_case = [val * (1 + improvement_factor) for val in forecast_values]

        forecast_result["scenarios"] = forecast_result.get("scenarios", {})
        forecast_result["scenarios"]["best_case"] = {
            "forecast_values": best_case,
            "improvement_factor": improvement_factor,
            "avg_value": np.mean(best_case),
        }

        return forecast_result

    async def generate_worst_case_scenario(
        self,
        forecast_result: dict[str, Any],
        deterioration_factor: float = 0.15,
    ) -> dict[str, Any]:
        """
        Generate worst-case scenario forecast.

        Feature #136: Worst-case scenario modeling
        """
        forecast_values = forecast_result["forecast_values"]

        # Worst case: deteriorate by deterioration_factor
        worst_case = [max(0, val * (1 - deterioration_factor)) for val in forecast_values]

        forecast_result["scenarios"] = forecast_result.get("scenarios", {})
        forecast_result["scenarios"]["worst_case"] = {
            "forecast_values": worst_case,
            "deterioration_factor": deterioration_factor,
            "avg_value": np.mean(worst_case),
        }

        return forecast_result

    async def generate_likely_case_scenario(
        self,
        forecast_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate likely/expected scenario forecast.

        Feature #137: Likely-case scenario modeling
        """
        forecast_values = forecast_result["forecast_values"]

        # Likely case: the baseline forecast with minor adjustment
        likely_case = forecast_values  # Already the most likely scenario

        forecast_result["scenarios"] = forecast_result.get("scenarios", {})
        forecast_result["scenarios"]["likely_case"] = {
            "forecast_values": likely_case,
            "avg_value": np.mean(likely_case),
            "description": "baseline_forecast",
        }

        return forecast_result

    def _exponential_smoothing_forecast(
        self,
        values: list[float],
        periods: int,
        alpha: float = 0.3,
    ) -> list[float]:
        """
        Simple exponential smoothing forecast.

        Args:
            values: Historical values
            periods: Number of periods to forecast
            alpha: Smoothing parameter (0-1)
        """
        if not values:
            return [0.0] * periods

        # Initialize with first value
        smoothed = [values[0]]

        # Calculate smoothed values for historical data
        for i in range(1, len(values)):
            smoothed_value = alpha * values[i] + (1 - alpha) * smoothed[i - 1]
            smoothed.append(smoothed_value)

        # Forecast future periods (constant forecast from last smoothed value)
        last_smoothed = smoothed[-1]
        forecast = [last_smoothed] * periods

        return forecast


# Singleton instance
forecasting_service = ForecastingService()
