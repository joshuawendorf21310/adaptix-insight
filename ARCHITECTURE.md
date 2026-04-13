# Adaptix Insight Architecture

## Overview

Adaptix Insight is the authoritative analytics, intelligence, and reporting platform for the Adaptix EMS ecosystem. It aggregates operational data from source domains, derives intelligence through KPI calculations and trend analysis, and provides executive-ready insights, scorecards, and reports.

## Architecture Principles

1. **Insight Never Owns Operational Data** - Insight consumes and aggregates but never becomes the system of record for CAD, ePCR, or other operational domains.

2. **Tenant Isolation is Mandatory** - All data is strictly isolated by `tenant_id` at database, service, and API layers.

3. **Idempotent Ingestion** - All analytics ingestion is replay-safe using idempotency keys and duplicate suppression.

4. **Deterministic Math Over AI** - KPI calculations use deterministic formulas, not AI inference. AI may assist with narrative generation but never core metrics.

5. **PHI Redaction** - Patient-identifiable information is redacted from aggregated insights and reports.

6. **Source Attribution** - All derived data preserves attribution to source domain and original event timestamps.

7. **Data Quality First** - Every metric includes quality scores, freshness indicators, and completeness checks.

## System Components

### 1. Ingestion Layer

**Purpose**: Accept analytics events from upstream domains.

**Components**:
- `ingestion_router.py` - API endpoints for event ingestion
- `ingestion_service.py` - Business logic for event validation and storage
- `AnalyticsEvent` model - Raw event storage with tenant isolation

**Features**:
- Single event ingestion (`POST /api/insight/ingestion/event`)
- Batch ingestion (`POST /api/insight/ingestion/batch`)
- Snapshot ingestion (`POST /api/insight/ingestion/snapshot`)
- Idempotency via `idempotency_key`
- Duplicate suppression
- Correlation ID support for distributed tracing
- Ingestion audit trail

**Data Flow**:
```
Source Domain → Ingestion API → IngestionService → AnalyticsEvent (DB)
                                           ↓
                                   IngestionAuditLog (DB)
```

### 2. Aggregation Pipelines

**Purpose**: Roll up raw events into time-based and dimensional aggregations.

**Components**:
- `aggregation_service.py` - Aggregation logic
- `DomainRollup` model - Domain-level aggregations
- `TenantRollup` model - Tenant-level aggregations

**Aggregation Levels**:
- Hourly (planned)
- Daily
- Weekly
- Monthly
- Quarterly
- Yearly

**Data Flow**:
```
AnalyticsEvent → AggregationService → DomainRollup (by domain + time)
                                   → TenantRollup (across domains + time)
```

**Scheduled Jobs** (implementation in progress):
- Hourly: Run hourly aggregations at :05 past the hour
- Daily: Run daily aggregations at 01:00 UTC
- Weekly: Run weekly aggregations on Mondays at 02:00 UTC
- Monthly: Run monthly aggregations on 1st of month at 03:00 UTC

### 3. KPI Engine

**Purpose**: Calculate and track Key Performance Indicators.

**Components**:
- `kpi_service.py` - KPI calculation and storage
- `KPIDefinition` model - KPI registry with formulas
- `KPIValue` model - Calculated KPI values

**KPI Categories**:
- **Operational**: response_time, turnout_time, scene_time, transport_time
- **Documentation**: chart_completion, nemsis_readiness
- **Financial**: billing_throughput, denial_rate
- **Workforce**: staffing_coverage, fatigue_risk
- **Utilization**: unit_utilization, apparatus_utilization
- **Business**: roi_realization, ai_usage

**KPI Calculation Flow**:
```
DomainRollup/TenantRollup → KPIService.calculate() → KPIValue (DB)
                                                   ↓
                                            Status Classification
                                            Trend Direction
                                            Target Comparison
```

### 4. Scorecard System

**Purpose**: Assemble multi-metric views for different stakeholder roles.

**Components**:
- `scorecard_service.py` - Scorecard assembly logic
- `scorecard_router.py` - Scorecard API endpoints

**Scorecard Types**:
- **Executive**: High-level operational, financial, and ROI metrics
- **Operational**: Detailed operational performance metrics
- **Billing**: Revenue cycle and claims metrics
- **Investor**: ROI, growth, and product adoption metrics
- **Agency**: (planned) Agency-specific performance
- **Station**: (planned) Station-level operations
- **Crew**: (planned) Crew performance and fatigue

**Data Flow**:
```
KPIValue (multiple KPIs) → ScorecardService.assemble() → ScorecardResponse
```

### 5. Benchmarking Engine

**Purpose**: Compare tenant performance to peer groups and historical baselines.

**Components**:
- `benchmark_service.py` - Comparison and ranking logic
- `Benchmark` model - Benchmark comparison data

**Benchmark Types**:
- Peer-group comparison (compare to similar agencies)
- Historical self-benchmark (compare to own past performance)
- Percentile ranking (0-100)
- Quartile classification (1-4)
- Outlier detection (IQR method)

**Data Flow**:
```
KPIValue (tenant) + Benchmark (peers) → BenchmarkService → BenchmarkResponse
                                                         ↓
                                                  Percentile Rank
                                                  Quartile
                                                  Outlier Status
```

### 6. Reporting Layer

**Purpose**: Generate and export reports in multiple formats.

**Components**:
- `report_service.py` - Report generation and export
- `ReportDefinition` model - Saved report templates

**Export Formats**:
- JSON (structured data)
- CSV (tabular data)
- PDF payload (ready for PDF rendering)

**Widget Payloads**:
- Dashboard widgets
- Chart-ready series (sparkline, bar, line, funnel)
- Heatmap payloads
- Map-insight payloads

**Data Flow**:
```
ReportRequest → ReportService.generate() → Query Data → Format → ReportResponse
                                                                ↓
                                                        CSV/JSON/PDF
```

### 7. Data Quality Monitoring

**Purpose**: Track data freshness, completeness, and quality.

**Components**:
- `data_quality_service.py` - Quality checking logic
- `DataQualityMetric` model - Quality metrics storage

**Quality Checks**:
- Source freshness (time since last data)
- Stale data warnings (>6 hours = degraded, >24 hours = unhealthy)
- Completeness scoring (0-1 scale)
- Metric quality scoring

**Data Flow**:
```
AnalyticsEvent (by domain) → DataQualityService.check() → DataQualityStatus
                                                         ↓
                                                  Freshness
                                                  Completeness
                                                  Warnings
```

## Database Schema

### Core Tables

**analytics_events**
- Primary table for raw analytics events
- Indexed on: `tenant_id`, `source_domain`, `event_timestamp`
- Unique constraint on `idempotency_key`

**ingestion_audit_logs**
- Audit trail for all ingestion operations
- Tracks successes, failures, and duplicates

**domain_rollups**
- Domain-level time-based aggregations
- Unique index on `(tenant_id, source_domain, aggregation_level, period_start)`

**tenant_rollups**
- Tenant-level aggregations across all domains
- Unique index on `(tenant_id, aggregation_level, period_start)`

**kpi_definitions**
- KPI registry with formulas and thresholds
- Unique index on `kpi_code`

**kpi_values**
- Calculated KPI values
- Unique index on `(tenant_id, kpi_code, aggregation_level, period_start)`

**benchmarks**
- Benchmark comparison data
- Indexed on `(tenant_id, metric_name, period_start)`

**report_definitions**
- Saved report templates
- Indexed on `tenant_id`

**data_quality_metrics**
- Quality and freshness tracking
- Indexed on `(tenant_id, source_domain, created_at)`

## API Architecture

### RESTful Endpoints

All APIs are RESTful HTTP/JSON under `/api/insight/*`.

**Base URL**: `http://localhost:8000` (development)

### API Versioning

Currently v1 implicit. Future versions will use `/api/v2/insight/*`.

### Authentication

Development: Dev auth enabled via `ADAPTIX_INSIGHT_ALLOW_DEV_AUTH=true`

Production: JWT-based authentication (implementation in progress)

### Request/Response Format

All requests and responses use JSON.

Request bodies are validated using Pydantic models.

Response models enforce type safety and documentation.

### Error Handling

- 400: Bad Request (validation errors)
- 401: Unauthorized (authentication required)
- 403: Forbidden (tenant isolation violation)
- 404: Not Found
- 500: Internal Server Error

## Observability

### Logging

- **Library**: structlog
- **Format**: JSON in production, console in development
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Fields**: timestamp, logger, level, message, context

### Tracing

- **Library**: OpenTelemetry (optional)
- **Exporter**: OTLP (configurable)
- **Sampling**: Always-on for errors, sampled for normal operations

### Metrics

- **Library**: Prometheus client
- **Endpoint**: `/metrics`
- **Metrics**: Request count, latency, error rate, database pool size

### Health Checks

- **Endpoint**: `GET /health`
- **Components**: Database, (future: Redis, upstream services)
- **States**: healthy, degraded, unhealthy

## Deployment Architecture

### Docker

Multi-stage build:
1. Builder stage: Install dependencies
2. Runtime stage: Minimal Python runtime

**Image Size**: ~300MB (optimized)

**User**: Non-root user `insight` (UID 1000)

### ECS Deployment

**Task Definition**:
- CPU: 512-1024 vCPU
- Memory: 1-2 GB
- Environment variables from Secrets Manager
- Logs to CloudWatch

**Service**:
- Target: 2 tasks (minimum)
- Load balancer: ALB with health checks
- Auto-scaling: CPU > 70%

### Database

**PostgreSQL 16+** via AWS RDS:
- Multi-AZ for production
- Read replicas for analytics queries (planned)
- Automated backups (7-day retention)
- Point-in-time recovery enabled

### Secrets Management

Production secrets stored in AWS Secrets Manager:
- Database credentials
- API keys
- JWT signing keys

## Security

### Tenant Isolation

- All queries filter by `tenant_id`
- Database row-level security (planned)
- API-level tenant validation

### PHI Redaction

- Patient-identifiable fields excluded from aggregations
- Redaction rules applied at ingestion
- Audit logs track PHI access

### Input Validation

- Pydantic models validate all inputs
- SQL injection prevention via SQLAlchemy
- XSS prevention on API responses

## Performance Considerations

### Database Indexing

All high-cardinality queries indexed:
- `(tenant_id, event_timestamp)`
- `(tenant_id, source_domain, event_timestamp)`
- `(tenant_id, kpi_code, period_start)`

### Caching

(Planned) Redis for:
- KPI values (5-minute TTL)
- Scorecard responses (15-minute TTL)
- Report results (1-hour TTL)

### Async I/O

All database operations are async using `asyncpg` and SQLAlchemy 2.0.

FastAPI async endpoints for non-blocking I/O.

## Data Retention

Default retention policies (configurable):

- **Raw events**: 730 days (2 years)
- **Aggregated data**: 2,555 days (7 years)
- **Audit logs**: 2,555 days (7 years)

Archival to S3 (planned):
- Raw events > 2 years → S3 Glacier
- Aggregations > 7 years → S3 Glacier Deep Archive

## Future Enhancements

1. **Real-time Aggregation**: Stream processing with Apache Flink
2. **Advanced Analytics**: Cohort analysis, retention curves, conversion funnels
3. **Forecasting**: Time-series forecasting with Prophet or ARIMA
4. **AI Insights**: GPT-powered narrative generation for trends and anomalies
5. **Alerting**: Proactive alerts for KPI threshold breaches
6. **Data Warehouse Sync**: Sync aggregations to Snowflake/BigQuery
7. **GraphQL API**: For flexible client-driven queries
8. **WebSocket Subscriptions**: Real-time scorecard updates
