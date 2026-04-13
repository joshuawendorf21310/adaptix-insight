# Adaptix Insight

**Adaptix Insight** is the authoritative analytics, intelligence, reporting, performance analysis, trend detection, benchmarking, forecasting, and executive decision-support platform for the Adaptix EMS ecosystem.

## Domain Ownership

Adaptix Insight is the **system of record** for:

- **Cross-domain analytics and derived intelligence**
- **KPI definitions, calculations, and tracking**
- **Executive, operational, and service-line scorecards**
- **Benchmarking and performance comparison**
- **Trend detection and pattern analysis**
- **Reporting models and export capabilities**
- **Forecasting support and scenario modeling**
- **Business and operational insights**
- **Data quality metrics and freshness tracking**

### What Insight Owns

- Aggregated analytics rollups (domain, tenant, agency, time-based)
- KPI registry, formulas, and calculated values
- Scorecard definitions and metric assemblies
- Benchmark comparison logic and peer-group analytics
- Report definitions, templates, and export formats
- Trend analysis and anomaly detection models
- Forecasting inputs and scenario support
- Executive insight summaries and narratives
- Data quality scores and completeness metrics

### What Insight Does NOT Own

Adaptix Insight **does not** own authoritative operational data. It consumes and aggregates data from:

- **CAD** - Computer-Aided Dispatch events
- **ePCR** - Electronic Patient Care Records
- **CrewLink** - Crew management and scheduling
- **Field** - Field operations and apparatus tracking
- **Air** - Air ambulance operations
- **Fire** - Fire and rescue operations
- **Workforce** - Personnel and staffing
- **TransportLink** - Transport coordination
- **Billing** - Revenue cycle and claims
- **Pulse** - Patient engagement
- **Command** - Command center operations
- **AI** - AI-powered features and usage

Insight aggregates, models, and derives intelligence from these domains but **never becomes their system of record**.

---

## Architecture

### Tech Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL 16+ with SQLAlchemy 2.0 (async)
- **Logging**: Structlog (structured JSON logging)
- **Observability**: OpenTelemetry (optional tracing)
- **Testing**: pytest with async support
- **Deployment**: Docker + ECS-compatible

### Key Components

1. **Ingestion Layer** - Accepts analytics events from source domains
2. **Storage Layer** - PostgreSQL with tenant-isolated schemas
3. **Aggregation Pipelines** - Time-based and dimensional rollups
4. **KPI Engine** - Definition registry and calculation engine
5. **Scorecard System** - Multi-level metric assemblies
6. **Benchmarking Engine** - Peer comparison and percentile ranking
7. **Trend Analysis** - Pattern detection and anomaly identification
8. **Reporting Layer** - Report builder and export engine
9. **Forecast Support** - Volume and demand forecasting inputs
10. **Insight APIs** - Role-specific intelligence endpoints

---

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL 16+ (or use Docker Compose)
- Docker + Docker Compose (recommended)

### Quick Start with Docker

```bash
# Clone repository
git clone git@github.com:joshuawendorf21310/adaptix-insight.git
cd adaptix-insight

# Start services with Docker Compose
docker-compose up -d

# Check health
curl http://localhost:8000/health

# View logs
docker-compose logs -f backend
```

The backend will be available at `http://localhost:8000`.

### API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Local Development without Docker

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Copy environment file
cp .env.example .env

# Edit .env with your database credentials

# Start PostgreSQL (if not using Docker)
# Ensure PostgreSQL is running and database 'adaptix_insight' exists

# Run application
uvicorn core_app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
cd backend

# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=core_app --cov-report=html

# Run specific test file
pytest tests/test_ingestion.py -v
```

---

## Environment Variables

All configuration is managed via environment variables with the prefix `ADAPTIX_INSIGHT_`.

### Required Variables

- `ADAPTIX_INSIGHT_DATABASE_URL` - Async PostgreSQL connection URL
- `ADAPTIX_INSIGHT_DATABASE_URL_SYNC` - Sync PostgreSQL connection URL (for migrations)

### Optional Variables (with defaults)

See `backend/.env.example` for full list of environment variables and their defaults.

### Secrets Management

**Production secrets** (not checked into source control):

- Database credentials
- API keys for external services
- JWT signing keys (when implemented)
- OTLP trace exporter credentials

Store production secrets in:
- **AWS Secrets Manager** (for ECS deployments)
- **Kubernetes Secrets** (for K8s deployments)
- **Environment variables** (injected at runtime)

---

## API Endpoints

### Core Analytics Endpoints

#### Ingestion

- `POST /api/insight/ingestion/event` - Ingest single analytics event
- `POST /api/insight/ingestion/batch` - Ingest batch of events
- `POST /api/insight/ingestion/snapshot` - Ingest snapshot event

#### KPIs

- `POST /api/insight/kpi/values` - Retrieve KPI values for time period

#### Scorecards (Coming Soon)

- `GET /api/insight/scorecard/executive` - Executive scorecard
- `GET /api/insight/scorecard/operational` - Operational scorecard
- `GET /api/insight/scorecard/agency` - Agency-level scorecard

#### Benchmarking (Coming Soon)

- `POST /api/insight/benchmark/compare` - Compare against peer group
- `GET /api/insight/benchmark/quartile` - Quartile ranking

#### Reporting (Coming Soon)

- `POST /api/insight/report/generate` - Generate report
- `GET /api/insight/report/definitions` - List saved report definitions

### Health & Observability

- `GET /health` - Enhanced health check with component status
- `GET /metrics` - Prometheus metrics (legacy)

---

## Database Schema

Adaptix Insight uses PostgreSQL with the following core tables:

### Ingestion
- `analytics_events` - Raw analytics event storage
- `ingestion_audit_logs` - Audit trail for ingestion

### Aggregations
- `domain_rollups` - Domain-level aggregations
- `tenant_rollups` - Tenant-level aggregations

### KPIs
- `kpi_definitions` - KPI registry with formulas
- `kpi_values` - Calculated KPI values

### Benchmarking
- `benchmarks` - Benchmark comparison data

### Reporting
- `report_definitions` - Saved report definitions

### Data Quality
- `data_quality_metrics` - Data quality and freshness tracking

All tables are tenant-isolated with indexed `tenant_id` columns.

---

## Data Retention

Default retention policies (configurable via environment variables):

- **Raw analytics events**: 730 days (2 years)
- **Aggregated data**: 2,555 days (7 years)
- **Audit logs**: 2,555 days (7 years)

Retention policies enforced via scheduled cleanup jobs (implementation in progress).

---

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t adaptix-insight:latest ./backend

# Run container
docker run -p 8000:8000 \
  -e ADAPTIX_INSIGHT_DATABASE_URL="postgresql+asyncpg://..." \
  -e ADAPTIX_INSIGHT_ENV=production \
  adaptix-insight:latest
```

### AWS ECS Deployment

The application is ECS-compatible:

- Uses multi-stage Docker builds for minimal image size
- Runs as non-root user
- Includes health check endpoint
- Supports graceful shutdown
- Structured JSON logging for CloudWatch

**Task Definition Requirements**:
- CPU: 512-1024
- Memory: 1GB-2GB
- Environment variables injected from AWS Secrets Manager
- Database connection via RDS endpoint

---

## Testing

### Test Structure

```
backend/tests/
├── test_ingestion.py       # Ingestion endpoint tests
├── test_kpi.py             # KPI calculation tests
├── test_scorecard.py       # Scorecard tests
├── test_benchmark.py       # Benchmarking tests
├── test_tenant_isolation.py # Tenant isolation tests
└── conftest.py             # Shared test fixtures
```

### Test Coverage Goals

- **Unit tests**: Service-layer logic, KPI formulas
- **Integration tests**: API endpoints with database
- **Contract tests**: Request/response schema validation
- **Isolation tests**: Tenant data separation

---

## Features Implemented

### Phase 1: Foundation (Features 1-17, 31-40, 164, 172-173, 191)

✅ Analytics ingestion endpoint
✅ Reporting ingestion endpoint
✅ Batch import endpoint
✅ Snapshot ingestion endpoint
✅ Typed analytics schema
✅ Typed KPI schema
✅ Tenant-safe analytics isolation
✅ Source-domain attribution
✅ Correlation ID support
✅ Idempotent ingestion handling
✅ Duplicate snapshot suppression
✅ Replay-safe analytics ingestion
✅ Ingestion audit trail
✅ KPI definition registry
✅ KPI formula versioning
✅ KPI status classification
✅ KPI target comparison
✅ KPI delta comparison
✅ KPI trend direction classification
✅ Self-health endpoint
✅ Typed request models
✅ Typed response models
✅ Docker support
✅ Structured logging
✅ Database lifecycle management

### Remaining Features (In Progress)

Features 18-200 are being implemented in subsequent phases, including:
- Aggregation pipelines
- Complete KPI suite
- Scorecard system
- Benchmarking engine
- Trend analysis
- Reporting layer
- Forecasting support
- Executive insights
- Comprehensive testing
- Full documentation

---

## Architecture Principles

1. **Insight is never the system of record for operational data**
2. **Tenant isolation is mandatory at all layers**
3. **All analytics ingestion is idempotent and replay-safe**
4. **KPI calculations use deterministic math, not AI**
5. **PHI is redacted from aggregated insights**
6. **Data quality scores accompany all metrics**
7. **Degraded upstream sources trigger warnings**
8. **Source attribution is preserved for all derived data**

---

## Development Workflow

### Adding a New KPI

1. Add KPI definition to `kpi_service.py` in `seed_kpi_definitions()`
2. Implement calculation logic in aggregation pipeline
3. Add tests for formula validation
4. Document KPI in this README
5. Update API documentation

### Adding a New Scorecard

1. Define scorecard structure in `schemas.py`
2. Implement scorecard assembly logic in `scorecard_service.py`
3. Add API endpoint in `scorecard_router.py`
4. Add integration tests
5. Document scorecard metrics

---

## Forbidden Drift

**Do NOT**:

- Make Insight the system of record for operational data (CAD, ePCR, etc.)
- Store raw PHI in aggregated tables
- Create circular dependencies on source domains
- Bypass tenant isolation
- Use AI for deterministic calculations (KPIs, metrics)
- Ingest data without source attribution
- Suppress errors silently

---

## Contributing

This repository is the authoritative boundary for Adaptix Insight analytics and intelligence.

For questions or contributions, contact the Insight platform team.

---

## License

Proprietary - Adaptix Platform
