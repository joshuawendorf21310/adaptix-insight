"""Analytics ingestion service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.models import AnalyticsEvent, IngestionAuditLog
from core_app.schemas import AnalyticsIngestionRequest, BatchIngestionRequest, BatchIngestionResponse, IngestionResponse

logger = get_logger(__name__)


class IngestionService:
    """Service for analytics event ingestion."""

    async def ingest_event(
        self, db: AsyncSession, request: AnalyticsIngestionRequest
    ) -> IngestionResponse:
        """
        Ingest a single analytics event.

        Features:
        - Tenant-safe isolation
        - Source domain attribution
        - Correlation ID support
        - Idempotent ingestion handling
        - Duplicate suppression
        - Ingestion audit trail
        """
        try:
            # Check for duplicate based on idempotency key
            if request.idempotency_key:
                existing = await db.execute(
                    select(AnalyticsEvent).where(AnalyticsEvent.idempotency_key == request.idempotency_key)
                )
                if existing.scalar_one_or_none():
                    logger.info(
                        "duplicate_event_suppressed",
                        idempotency_key=request.idempotency_key,
                        tenant_id=str(request.tenant_id),
                    )
                    await self._log_audit(
                        db=db,
                        tenant_id=request.tenant_id,
                        source_domain=request.source_domain.value,
                        action="ingest_event",
                        status="duplicate",
                        metadata={"idempotency_key": request.idempotency_key},
                    )
                    return IngestionResponse(
                        event_id=None,
                        status="suppressed",
                        message="Duplicate event detected",
                        duplicate=True,
                    )

            # Create analytics event
            event = AnalyticsEvent(
                id=uuid.uuid4(),
                tenant_id=request.tenant_id,
                source_domain=request.source_domain.value,
                event_type=request.event_type,
                event_timestamp=request.event_timestamp,
                correlation_id=request.correlation_id,
                idempotency_key=request.idempotency_key,
                payload=request.payload,
                metadata=request.metadata,
                created_at=datetime.now(),
            )

            db.add(event)
            await db.flush()

            # Log successful ingestion
            await self._log_audit(
                db=db,
                tenant_id=request.tenant_id,
                source_domain=request.source_domain.value,
                action="ingest_event",
                status="success",
                event_id=event.id,
                metadata={"event_type": request.event_type},
            )

            logger.info(
                "event_ingested",
                event_id=str(event.id),
                tenant_id=str(request.tenant_id),
                source_domain=request.source_domain.value,
                event_type=request.event_type,
            )

            return IngestionResponse(
                event_id=event.id,
                status="accepted",
                message="Event successfully ingested",
                duplicate=False,
            )

        except Exception as e:
            logger.error("event_ingestion_failed", error=str(e), tenant_id=str(request.tenant_id))
            await self._log_audit(
                db=db,
                tenant_id=request.tenant_id,
                source_domain=request.source_domain.value,
                action="ingest_event",
                status="error",
                error_message=str(e),
            )
            raise

    async def ingest_batch(
        self, db: AsyncSession, request: BatchIngestionRequest
    ) -> BatchIngestionResponse:
        """
        Ingest a batch of analytics events.

        Features:
        - Batch import endpoint
        - Per-event validation
        - Partial success handling
        - Duplicate detection across batch
        """
        results: list[IngestionResponse] = []
        accepted = 0
        rejected = 0
        duplicates = 0

        for event_request in request.events:
            try:
                result = await self.ingest_event(db, event_request)
                results.append(result)

                if result.status == "accepted":
                    accepted += 1
                elif result.duplicate:
                    duplicates += 1
                else:
                    rejected += 1

            except Exception as e:
                logger.error("batch_event_failed", error=str(e))
                results.append(
                    IngestionResponse(
                        event_id=None,
                        status="rejected",
                        message=f"Error: {str(e)}",
                        duplicate=False,
                    )
                )
                rejected += 1

        logger.info(
            "batch_ingestion_completed",
            total=len(request.events),
            accepted=accepted,
            rejected=rejected,
            duplicates=duplicates,
        )

        return BatchIngestionResponse(
            total=len(request.events),
            accepted=accepted,
            rejected=rejected,
            duplicates=duplicates,
            results=results,
        )

    async def _log_audit(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        source_domain: str,
        action: str,
        status: str,
        event_id: uuid.UUID | None = None,
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Log ingestion audit entry."""
        audit_log = IngestionAuditLog(
            tenant_id=tenant_id,
            event_id=event_id,
            source_domain=source_domain,
            action=action,
            status=status,
            error_message=error_message,
            metadata=metadata,
        )
        db.add(audit_log)
        await db.flush()


# Singleton instance
ingestion_service = IngestionService()
