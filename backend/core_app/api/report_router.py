"""Report API endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.schemas import ReportRequest, ReportResponse
from core_app.services.report_service import report_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/insight/report", tags=["Reporting"])


@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """
    Generate a report.

    Features implemented:
    - Report builder API (Feature #101)
    - Report export to CSV (Feature #105)
    - Report export to JSON (Feature #106)
    - Report export to PDF payload (Feature #107)
    - Dashboard widget payloads (Feature #108)
    - Chart-ready series payloads (Feature #109)
    """
    try:
        return await report_service.generate_report(db, request)
    except Exception as e:
        logger.error("report_generation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/definitions")
async def get_report_definitions(
    tenant_id: UUID = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get saved report definitions.

    Features implemented:
    - Saved report definitions (Feature #102)
    - Report scheduling metadata (Feature #103)
    - Report parameter templates (Feature #104)
    """
    try:
        definitions = await report_service.get_report_definitions(db, tenant_id)
        return {"definitions": [
            {
                "id": str(d.id),
                "report_name": d.report_name,
                "report_type": d.report_type,
                "description": d.description,
                "parameters": d.parameters,
                "schedule_config": d.schedule_config,
                "export_formats": d.export_formats,
            }
            for d in definitions
        ]}
    except Exception as e:
        logger.error("get_report_definitions_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get report definitions: {str(e)}",
        )
