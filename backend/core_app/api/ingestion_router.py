"""Analytics ingestion API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.schemas import (
    AnalyticsIngestionRequest,
    BatchIngestionRequest,
    BatchIngestionResponse,
    IngestionResponse,
)
from core_app.services.ingestion_service import ingestion_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/insight/ingestion", tags=["Analytics Ingestion"])


@router.post("/event", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
async def ingest_analytics_event(
    request: AnalyticsIngestionRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Ingest a single analytics event.

    Features implemented:
    - Analytics ingestion endpoint (Feature #1)
    - Typed analytics schema (Feature #6)
    - Tenant-safe analytics isolation (Feature #11)
    - Source-domain attribution (Feature #12)
    - Correlation id support (Feature #13)
    - Idempotent ingestion handling (Feature #14)
    - Duplicate snapshot suppression (Feature #15)
    - Replay-safe analytics ingestion (Feature #16)
    - Ingestion audit trail (Feature #17)
    """
    try:
        result = await ingestion_service.ingest_event(db, request)
        return result
    except Exception as e:
        logger.error("ingestion_endpoint_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest event: {str(e)}",
        )


@router.post("/batch", response_model=BatchIngestionResponse, status_code=status.HTTP_201_CREATED)
async def ingest_batch_events(
    request: BatchIngestionRequest,
    db: AsyncSession = Depends(get_db),
) -> BatchIngestionResponse:
    """
    Ingest a batch of analytics events.

    Features implemented:
    - Batch import endpoint (Feature #3)
    - All features from single event ingestion
    """
    try:
        result = await ingestion_service.ingest_batch(db, request)
        return result
    except Exception as e:
        logger.error("batch_ingestion_endpoint_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest batch: {str(e)}",
        )


@router.post("/snapshot", response_model=IngestionResponse, status_code=status.HTTP_201_CREATED)
async def ingest_snapshot(
    request: AnalyticsIngestionRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestionResponse:
    """
    Ingest a snapshot event (identical to analytics ingestion with duplicate suppression).

    Features implemented:
    - Snapshot ingestion endpoint (Feature #5)
    - Duplicate snapshot suppression (Feature #15)
    """
    # Snapshots are handled identically to regular events
    # Idempotency key should be used for duplicate suppression
    return await ingest_analytics_event(request, db)
