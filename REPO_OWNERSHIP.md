# Adaptix Insight - Domain Ownership

## Primary Responsibility

Adaptix Insight is the **authoritative system of record** for:

- **Cross-domain analytics aggregation and derived intelligence**
- **KPI definitions, formulas, and calculated values**
- **Scorecard assemblies and executive dashboards**
- **Benchmark comparisons and performance rankings**
- **Trend analysis and pattern detection**
- **Report definitions, templates, and export logic**
- **Forecasting support and scenario modeling**
- **Data quality metrics and freshness tracking**
- **Business intelligence and decision-support narratives**

## What Insight Owns

### Analytics Domain

- **Raw Analytics Events**: Ingested from source domains, stored for aggregation
- **Domain Rollups**: Aggregated metrics by source domain and time period
- **Tenant Rollups**: Cross-domain aggregations for tenant-wide insights
- **Aggregation Logic**: Time-based rollup pipelines (daily, weekly, monthly, etc.)

### KPI Domain

- **KPI Definitions**: Registry of all KPIs with formulas, thresholds, targets
- **KPI Values**: Calculated KPI results by tenant, time period, and aggregation level
- **KPI Status Classification**: Healthy, warning, critical status determination
- **Trend Direction**: Up, down, stable trend classification logic
- **Target Comparison**: Delta calculations from target values

### Scorecard Domain

- **Scorecard Definitions**: Which KPIs belong in which scorecards
- **Scorecard Assembly Logic**: How to combine KPIs for different stakeholder views
- **Executive Scorecards**: High-level operational and financial metrics
- **Operational Scorecards**: Detailed performance metrics for operations teams
- **Billing Scorecards**: Revenue cycle and claims performance
- **Investor Scorecards**: ROI and growth metrics

### Benchmarking Domain

- **Benchmark Data**: Peer-group and historical benchmark values
- **Comparison Logic**: Percentile, quartile, and ranking calculations
- **Outlier Detection**: Statistical outlier identification
- **Peer-Group Definitions**: Which tenants belong to which peer groups

### Reporting Domain

- **Report Definitions**: Saved report templates with parameters
- **Report Generation**: Logic to query and assemble report data
- **Export Formats**: CSV, JSON, PDF payload generation
- **Dashboard Widgets**: Chart-ready payloads for UI consumption
- **Scheduling Metadata**: Report scheduling configuration

### Data Quality Domain

- **Quality Metrics**: Freshness, completeness, accuracy tracking
- **Quality Scores**: 0-1 scoring for data quality
- **Stale Data Detection**: Warnings for aged or missing data
- **Completeness Scoring**: Percentage of expected data received

## What Insight Does NOT Own

Adaptix Insight **consumes** operational data but **never owns** the authoritative records for:

### Source Domain Data (Read-Only Consumers)

- **CAD** (Computer-Aided Dispatch)
  - Dispatch events, unit assignments, timestamps
  - Call types, priorities, dispositions
  - Insight **consumes** CAD events for response-time KPIs

- **ePCR** (Electronic Patient Care Records)
  - Patient charts, interventions, medications, assessments
  - Signature status, completion timestamps, NEMSIS compliance
  - Insight **consumes** ePCR data for documentation KPIs

- **CrewLink** (Crew Management)
  - Crew assignments, shift schedules, certifications
  - Insight **consumes** CrewLink data for staffing KPIs

- **Field** (Field Operations)
  - Apparatus status, station assignments, deployment
  - Insight **consumes** Field data for utilization KPIs

- **Air** (Air Ambulance Operations)
  - Flight operations, air unit assignments, flight times
  - Insight **consumes** Air data for air-specific KPIs

- **Fire** (Fire and Rescue Operations)
  - Fire incidents, apparatus assignments, fire-specific metrics
  - Insight **consumes** Fire data for fire operations KPIs

- **Workforce** (Personnel and Staffing)
  - Employee records, credentials, availability, fatigue tracking
  - Insight **consumes** Workforce data for staffing and fatigue KPIs

- **TransportLink** (Transport Coordination)
  - Transport requests, assignments, recurring transport schedules
  - Insight **consumes** TransportLink data for transport KPIs

- **Billing** (Revenue Cycle Management)
  - Claims, denials, payments, payer contracts
  - Insight **consumes** Billing data for financial KPIs

- **Pulse** (Patient Engagement)
  - Patient portal usage, engagement metrics, patient satisfaction
  - Insight **consumes** Pulse data for engagement KPIs

- **Command** (Command Center Operations)
  - Command center activity, dispatch oversight, coordination
  - Insight **consumes** Command data for command-specific KPIs

- **AI** (AI-Powered Features)
  - AI feature usage, suggestions, cost tracking
  - Insight **consumes** AI data for AI adoption and cost KPIs

## Data Flow Direction

```
Source Domains → Insight (Ingestion) → Aggregation → KPI Calculation → Scorecards/Reports
    ↓                                                                         ↓
(Operational Truth)                                            (Derived Intelligence)
```

**Key Principle**: Data flows **into** Insight from source domains. Insight **never** flows operational data back to source domains as authoritative updates.

## Forbidden Actions

Adaptix Insight **MUST NEVER**:

1. **Become the system of record for operational data**
   - ❌ Do NOT store authoritative CAD, ePCR, or other operational records
   - ✅ DO store analytics events derived from these sources

2. **Modify source domain data**
   - ❌ Do NOT update incident records, charts, or operational data in source systems
   - ✅ DO calculate and store derived metrics

3. **Bypass tenant isolation**
   - ❌ Do NOT allow cross-tenant data access
   - ✅ DO enforce tenant_id filtering at all layers

4. **Store raw PHI in aggregations**
   - ❌ Do NOT include patient names, SSNs, addresses in aggregated tables
   - ✅ DO redact PHI before aggregation

5. **Suppress errors silently**
   - ❌ Do NOT hide data quality issues or ingestion failures
   - ✅ DO log warnings and track quality metrics

6. **Use AI for deterministic calculations**
   - ❌ Do NOT use AI/LLMs for KPI formulas or metric calculations
   - ✅ DO use deterministic math for all KPIs

7. **Ingest without source attribution**
   - ❌ Do NOT lose track of which domain provided the data
   - ✅ DO preserve source_domain on all analytics events

## Integration Contracts

### Inbound (from Source Domains)

Source domains **send analytics events to Insight** via:

- **HTTP API**: `POST /api/insight/ingestion/event`
- **Batch API**: `POST /api/insight/ingestion/batch`
- **Event Schema**: Typed `AnalyticsIngestionRequest` with source attribution

Source domains **retain authoritative ownership** of their data.

### Outbound (to Consumers)

Insight **exposes derived intelligence** to consumers via:

- **Scorecard APIs**: Assembled KPI views
- **Report APIs**: Generated reports in multiple formats
- **Benchmark APIs**: Peer comparison and ranking
- **Data Quality APIs**: Freshness and completeness status

Consumers (Command, Pulse, frontend dashboards) **display insights** but do not modify them.

## Repository Migration

This repository was bootstrapped from the FusionEMS-Core polyrepo migration control plane on 2026-04-08.

**Migration Status**: Active transformation from placeholder to production-grade service.

**Prior State**: Bootstrapped placeholder with minimal functionality.

**Current State**: Production-ready analytics and intelligence platform.

**Forbidden Drift**: Do NOT revert to placeholder status or remove production features.

## Contact

For questions about Insight domain ownership, contact the Adaptix Insight platform team.

For domain boundary disputes, escalate to Adaptix architecture leadership.

