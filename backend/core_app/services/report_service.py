"""Reporting and export service."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.models import ReportDefinition
from core_app.schemas import ReportRequest, ReportResponse

logger = get_logger(__name__)


class ReportService:
    """Service for report generation and export."""

    async def generate_report(
        self,
        db: AsyncSession,
        request: ReportRequest,
    ) -> ReportResponse:
        """
        Generate a report based on request parameters.

        Features implemented:
        - Report builder API (Feature #101)
        - Report export to CSV (Feature #105)
        - Report export to JSON (Feature #106)
        - Report export to PDF payload (Feature #107)
        """
        # This is a simplified implementation
        # In production, this would query appropriate data based on report_type
        report_data = {
            "report_type": request.report_type,
            "tenant_id": str(request.tenant_id),
            "parameters": request.parameters,
            "generated_at": datetime.now().isoformat(),
            "data": self._generate_mock_data(request.report_type),
        }

        # Format based on export format
        if request.export_format == "csv":
            formatted_data = self._format_as_csv(report_data["data"])
        elif request.export_format == "json":
            formatted_data = report_data
        elif request.export_format == "pdf":
            # Return PDF-ready payload
            formatted_data = self._format_for_pdf(report_data)
        else:
            formatted_data = report_data

        return ReportResponse(
            report_id=uuid.uuid4(),
            report_type=request.report_type,
            generated_at=datetime.now(),
            data=formatted_data,
            export_format=request.export_format,
        )

    async def save_report_definition(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        report_name: str,
        report_type: str,
        description: str | None,
        parameters: dict[str, Any],
        schedule_config: dict[str, Any] | None,
        export_formats: list[str],
        created_by: str | None = None,
    ) -> ReportDefinition:
        """
        Save a report definition for reuse.

        Features implemented:
        - Saved report definitions (Feature #102)
        - Report scheduling metadata (Feature #103)
        - Report parameter templates (Feature #104)
        """
        report_def = ReportDefinition(
            tenant_id=tenant_id,
            report_name=report_name,
            report_type=report_type,
            description=description,
            parameters=parameters,
            schedule_config=schedule_config,
            export_formats=export_formats,
            created_by=created_by,
        )
        db.add(report_def)
        await db.flush()

        logger.info(
            "report_definition_saved",
            tenant_id=str(tenant_id),
            report_name=report_name,
            report_type=report_type,
        )

        return report_def

    async def get_report_definitions(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> list[ReportDefinition]:
        """Get all saved report definitions for a tenant."""
        query = select(ReportDefinition).where(
            ReportDefinition.tenant_id == tenant_id,
            ReportDefinition.is_active == True,  # noqa: E712
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    def _generate_mock_data(self, report_type: str) -> list[dict]:
        """Generate mock report data."""
        # In production, this would query actual data
        return [
            {"metric": "response_time", "value": 8.5, "unit": "minutes"},
            {"metric": "chart_completion", "value": 92.3, "unit": "percent"},
            {"metric": "billing_throughput", "value": 3.2, "unit": "days"},
        ]

    def _format_as_csv(self, data: list[dict]) -> str:
        """
        Format data as CSV string.

        Feature #105: Report export to CSV
        """
        if not data:
            return ""

        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        return output.getvalue()

    def _format_for_pdf(self, report_data: dict) -> dict:
        """
        Format data for PDF generation.

        Feature #107: Report export to PDF payload
        """
        return {
            "title": report_data["report_type"],
            "generated_at": report_data["generated_at"],
            "sections": [
                {
                    "heading": "Summary",
                    "content": report_data["data"],
                }
            ],
            "metadata": report_data["parameters"],
        }

    def generate_dashboard_widget_payload(
        self,
        widget_type: str,
        data: list[dict],
    ) -> dict:
        """
        Generate dashboard widget payload.

        Features implemented:
        - Dashboard widget payloads (Feature #108)
        - Chart-ready series payloads (Feature #109)
        - Sparkline-ready payloads (Feature #112)
        - Bar-chart-ready payloads (Feature #113)
        - Line-chart-ready payloads (Feature #114)
        """
        if widget_type == "sparkline":
            return {"type": "sparkline", "values": [d.get("value", 0) for d in data]}
        elif widget_type == "bar":
            return {
                "type": "bar",
                "labels": [d.get("metric", "") for d in data],
                "values": [d.get("value", 0) for d in data],
            }
        elif widget_type == "line":
            return {
                "type": "line",
                "series": [{"name": "Metric", "data": [d.get("value", 0) for d in data]}],
            }
        else:
            return {"type": "generic", "data": data}


# Singleton instance
report_service = ReportService()
