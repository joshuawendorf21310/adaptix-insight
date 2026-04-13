"""Pydantic schemas for Adaptix Insight API contracts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SourceDomainEnum(str, Enum):
    """Source domain enumeration for API."""

    CAD = "cad"
    EPCR = "epcr"
    CREWLINK = "crewlink"
    FIELD = "field"
    AIR = "air"
    FIRE = "fire"
    WORKFORCE = "workforce"
    TRANSPORT_LINK = "transportlink"
    BILLING = "billing"
    PULSE = "pulse"
    COMMAND = "command"
    AI = "ai"
    INSIGHT = "insight"


class AggregationLevelEnum(str, Enum):
    """Aggregation level enumeration."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class TrendDirection(str, Enum):
    """Trend direction classification."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"


class KPIStatus(str, Enum):
    """KPI status classification."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


# Ingestion Schemas


class AnalyticsIngestionRequest(BaseModel):
    """Analytics event ingestion request."""

    tenant_id: UUID = Field(description="Tenant identifier")
    source_domain: SourceDomainEnum = Field(description="Source domain")
    event_type: str = Field(description="Event type identifier")
    event_timestamp: datetime = Field(description="Event occurrence timestamp")
    correlation_id: str | None = Field(default=None, description="Correlation ID for tracing")
    idempotency_key: str | None = Field(default=None, description="Idempotency key for duplicate prevention")
    payload: dict[str, Any] = Field(description="Event payload data")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional metadata")


class BatchIngestionRequest(BaseModel):
    """Batch analytics ingestion request."""

    events: list[AnalyticsIngestionRequest] = Field(description="List of analytics events")


class IngestionResponse(BaseModel):
    """Analytics ingestion response."""

    event_id: UUID | None = Field(description="Assigned event ID")
    status: str = Field(description="Ingestion status")
    message: str | None = Field(default=None, description="Status message")
    duplicate: bool = Field(default=False, description="Whether this was a duplicate")


class BatchIngestionResponse(BaseModel):
    """Batch ingestion response."""

    total: int = Field(description="Total events submitted")
    accepted: int = Field(description="Events accepted")
    rejected: int = Field(description="Events rejected")
    duplicates: int = Field(description="Duplicate events suppressed")
    results: list[IngestionResponse] = Field(description="Individual event results")


# KPI Schemas


class KPIDefinitionSchema(BaseModel):
    """KPI definition schema."""

    id: UUID = Field(description="KPI definition ID")
    kpi_code: str = Field(description="Unique KPI code")
    kpi_name: str = Field(description="Human-readable KPI name")
    description: str | None = Field(default=None, description="KPI description")
    formula: str = Field(description="Calculation formula")
    formula_version: int = Field(description="Formula version")
    source_domains: list[str] = Field(description="Source domains")
    unit: str | None = Field(default=None, description="Unit of measurement")
    threshold_warning: float | None = Field(default=None, description="Warning threshold")
    threshold_critical: float | None = Field(default=None, description="Critical threshold")
    target_value: float | None = Field(default=None, description="Target value")
    owner: str | None = Field(default=None, description="KPI owner")
    is_active: bool = Field(description="Whether KPI is active")


class KPIValueSchema(BaseModel):
    """KPI value schema."""

    id: UUID = Field(description="KPI value ID")
    tenant_id: UUID = Field(description="Tenant ID")
    kpi_code: str = Field(description="KPI code")
    kpi_name: str | None = Field(default=None, description="KPI name")
    aggregation_level: AggregationLevelEnum = Field(description="Aggregation level")
    period_start: datetime = Field(description="Period start")
    period_end: datetime = Field(description="Period end")
    value: float = Field(description="Calculated value")
    status: KPIStatus | None = Field(default=None, description="Status classification")
    trend_direction: TrendDirection | None = Field(default=None, description="Trend direction")
    delta_from_previous: float | None = Field(default=None, description="Change from previous period")
    delta_from_target: float | None = Field(default=None, description="Distance from target")
    quality_score: float | None = Field(default=None, description="Data quality score")


class KPIListRequest(BaseModel):
    """KPI list query request."""

    tenant_id: UUID = Field(description="Tenant ID")
    kpi_codes: list[str] | None = Field(default=None, description="Filter by KPI codes")
    aggregation_level: AggregationLevelEnum = Field(description="Aggregation level")
    period_start: datetime = Field(description="Period start")
    period_end: datetime = Field(description="Period end")


class KPIListResponse(BaseModel):
    """KPI list response."""

    kpis: list[KPIValueSchema] = Field(description="KPI values")
    count: int = Field(description="Number of KPIs returned")


# Scorecard Schemas


class ScorecardMetric(BaseModel):
    """Scorecard metric item."""

    metric_code: str = Field(description="Metric code")
    metric_name: str = Field(description="Metric name")
    value: float = Field(description="Metric value")
    unit: str | None = Field(default=None, description="Unit")
    status: KPIStatus | None = Field(default=None, description="Status")
    trend_direction: TrendDirection | None = Field(default=None, description="Trend")
    delta_from_previous: float | None = Field(default=None, description="Change from previous")
    delta_from_target: float | None = Field(default=None, description="Distance from target")


class ScorecardResponse(BaseModel):
    """Scorecard response."""

    scorecard_type: str = Field(description="Scorecard type")
    tenant_id: UUID = Field(description="Tenant ID")
    period_start: datetime = Field(description="Period start")
    period_end: datetime = Field(description="Period end")
    metrics: list[ScorecardMetric] = Field(description="Scorecard metrics")
    summary: dict[str, Any] | None = Field(default=None, description="Summary data")


# Benchmark Schemas


class BenchmarkRequest(BaseModel):
    """Benchmark comparison request."""

    tenant_id: UUID = Field(description="Tenant ID")
    metric_name: str = Field(description="Metric to benchmark")
    period_start: datetime = Field(description="Period start")
    period_end: datetime = Field(description="Period end")
    comparison_type: str = Field(description="Benchmark type (peer, historical, percentile)")


class BenchmarkResponse(BaseModel):
    """Benchmark comparison response."""

    tenant_id: UUID = Field(description="Tenant ID")
    metric_name: str = Field(description="Metric name")
    value: float = Field(description="Tenant value")
    peer_group_avg: float | None = Field(default=None, description="Peer group average")
    peer_group_median: float | None = Field(default=None, description="Peer group median")
    percentile_rank: float | None = Field(default=None, description="Percentile rank")
    quartile: int | None = Field(default=None, description="Quartile (1-4)")
    comparison_metadata: dict[str, Any] | None = Field(default=None, description="Comparison metadata")


# Report Schemas


class ReportRequest(BaseModel):
    """Report generation request."""

    tenant_id: UUID = Field(description="Tenant ID")
    report_type: str = Field(description="Report type")
    parameters: dict[str, Any] = Field(description="Report parameters")
    export_format: str = Field(default="json", description="Export format (json, csv, pdf)")


class ReportResponse(BaseModel):
    """Report generation response."""

    report_id: UUID = Field(description="Report ID")
    report_type: str = Field(description="Report type")
    generated_at: datetime = Field(description="Generation timestamp")
    data: Any = Field(description="Report data")
    export_format: str = Field(description="Export format")


# Data Quality Schemas


class DataQualityStatus(BaseModel):
    """Data quality status."""

    source_domain: str = Field(description="Source domain")
    last_data_timestamp: datetime | None = Field(default=None, description="Last data received")
    completeness_score: float | None = Field(default=None, description="Completeness score (0-1)")
    status: str = Field(description="Overall status")
    warnings: list[str] = Field(default_factory=list, description="Quality warnings")


class DataQualityResponse(BaseModel):
    """Data quality response."""

    tenant_id: UUID = Field(description="Tenant ID")
    overall_status: str = Field(description="Overall quality status")
    domains: list[DataQualityStatus] = Field(description="Per-domain quality status")
    checked_at: datetime = Field(description="Check timestamp")


# Health and Status Schemas


class HealthStatus(str, Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Individual component health."""

    name: str = Field(description="Component name")
    status: HealthStatus = Field(description="Health status")
    message: str | None = Field(default=None, description="Status message")
    details: dict[str, Any] | None = Field(default=None, description="Additional details")


class HealthResponse(BaseModel):
    """Health check response."""

    status: HealthStatus = Field(description="Overall status")
    version: str = Field(description="Application version")
    timestamp: datetime = Field(description="Check timestamp")
    components: list[ComponentHealth] = Field(description="Component health status")
