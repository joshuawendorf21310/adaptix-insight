"""Adaptix Insight - Analytics, Intelligence, Reporting, and Decision Support Platform."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core_app.api.adaptix_insight_router import router as adaptix_insight_router
from core_app.api.auth_router import router as auth_router
from core_app.api.benchmark_router import router as benchmark_router
from core_app.api.commercial_router import router as commercial_router
from core_app.api.data_quality_router import router as data_quality_router
from core_app.api.founder_router import router as founder_router
from core_app.api.founder_surface_router import router as founder_surface_router
from core_app.api.health_router import router as health_router
from core_app.api.ingestion_router import router as ingestion_router
from core_app.api.kpi_router import router as kpi_router
from core_app.api.metrics_router import router as metrics_router
from core_app.api.report_router import router as report_router
from core_app.api.scorecard_router import router as scorecard_router
from core_app.api.system_health_shell_router import router as system_health_router
from core_app.config import settings
from core_app.db import close_db, get_db_context, init_db
from core_app.logging_config import configure_logging, get_logger
from core_app.schemas import ComponentHealth, HealthResponse, HealthStatus
from core_app.services.kpi_service import kpi_service

# Configure logging
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("adaptix_insight_starting", env=settings.app_env, version="0.1.0")

    # Initialize database
    await init_db()
    logger.info("database_initialized")

    # Seed KPI definitions
    async with get_db_context() as db:
        await kpi_service.seed_kpi_definitions(db)

    logger.info("adaptix_insight_started")

    yield

    # Cleanup
    logger.info("adaptix_insight_shutting_down")
    await close_db()
    logger.info("adaptix_insight_stopped")


app = FastAPI(
    title="Adaptix Insight",
    version="0.1.0",
    description="Analytics, Intelligence, Reporting, and Decision Support Platform",
    lifespan=lifespan,
)

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Insight routers
app.include_router(health_router)
app.include_router(ingestion_router)
app.include_router(kpi_router)
app.include_router(scorecard_router)
app.include_router(benchmark_router)
app.include_router(report_router)
app.include_router(data_quality_router)

# Legacy routers (for migration compatibility)
app.include_router(auth_router)
app.include_router(commercial_router)
app.include_router(founder_router)
app.include_router(founder_surface_router)
app.include_router(system_health_router)
app.include_router(metrics_router)
app.include_router(adaptix_insight_router)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Enhanced health check endpoint.

    Features implemented:
    - Self-health endpoint (Feature #164)
    - Component health monitoring
    """
    components = []

    # Check database
    try:
        async with get_db_context() as db:
            await db.execute("SELECT 1")
        components.append(
            ComponentHealth(
                name="database",
                status=HealthStatus.HEALTHY,
                message="Database connection OK",
            )
        )
    except Exception as e:
        components.append(
            ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
            )
        )

    # Overall status
    overall_status = HealthStatus.HEALTHY
    if any(c.status == HealthStatus.UNHEALTHY for c in components):
        overall_status = HealthStatus.UNHEALTHY
    elif any(c.status == HealthStatus.DEGRADED for c in components):
        overall_status = HealthStatus.DEGRADED

    return HealthResponse(
        status=overall_status,
        version="0.1.0",
        timestamp=datetime.now(),
        components=components,
    )