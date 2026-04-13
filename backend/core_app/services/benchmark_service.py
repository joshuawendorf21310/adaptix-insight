"""Benchmarking and comparison service."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.logging_config import get_logger
from core_app.models import Benchmark
from core_app.schemas import BenchmarkRequest, BenchmarkResponse

logger = get_logger(__name__)


class BenchmarkService:
    """Service for benchmark comparison and analysis."""

    async def create_benchmark(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        benchmark_type: str,
        metric_name: str,
        period_start: datetime,
        period_end: datetime,
        value: float,
        peer_group_avg: float | None = None,
        peer_group_median: float | None = None,
        peer_group_p25: float | None = None,
        peer_group_p75: float | None = None,
        percentile_rank: float | None = None,
        quartile: int | None = None,
        comparison_metadata: dict | None = None,
    ) -> Benchmark:
        """
        Store benchmark comparison data.

        Features #71-87: Benchmark comparison logic
        """
        benchmark = Benchmark(
            tenant_id=tenant_id,
            benchmark_type=benchmark_type,
            metric_name=metric_name,
            period_start=period_start,
            period_end=period_end,
            value=value,
            peer_group_avg=peer_group_avg,
            peer_group_median=peer_group_median,
            peer_group_p25=peer_group_p25,
            peer_group_p75=peer_group_p75,
            percentile_rank=percentile_rank,
            quartile=quartile,
            comparison_metadata=comparison_metadata,
        )
        db.add(benchmark)
        await db.flush()
        return benchmark

    async def compare_to_peer_group(
        self,
        db: AsyncSession,
        request: BenchmarkRequest,
    ) -> BenchmarkResponse:
        """
        Compare metric to peer group benchmarks.

        Features implemented:
        - Benchmark comparison engine (Feature #71)
        - Peer-group benchmark support (Feature #72)
        - Percentile ranking support (Feature #85)
        - Performance quartile ranking (Feature #84)
        """
        # Get all peer benchmarks for this metric and period
        query = select(Benchmark).where(
            Benchmark.metric_name == request.metric_name,
            Benchmark.period_start == request.period_start,
            Benchmark.period_end == request.period_end,
            Benchmark.benchmark_type == request.comparison_type,
        )

        result = await db.execute(query)
        benchmarks = result.scalars().all()

        if not benchmarks:
            # No peer data available
            return BenchmarkResponse(
                tenant_id=request.tenant_id,
                metric_name=request.metric_name,
                value=0.0,  # Would come from KPI values
                peer_group_avg=None,
                peer_group_median=None,
                percentile_rank=None,
                quartile=None,
                comparison_metadata={"status": "no_peer_data"},
            )

        # Calculate peer statistics
        values = [b.value for b in benchmarks]
        values.sort()

        peer_group_avg = sum(values) / len(values)
        peer_group_median = values[len(values) // 2]
        peer_group_p25 = values[len(values) // 4]
        peer_group_p75 = values[3 * len(values) // 4]

        # Find tenant's benchmark
        tenant_benchmark = next((b for b in benchmarks if b.tenant_id == request.tenant_id), None)

        if tenant_benchmark:
            tenant_value = tenant_benchmark.value
            # Calculate percentile rank
            lower_count = sum(1 for v in values if v < tenant_value)
            percentile_rank = (lower_count / len(values)) * 100

            # Calculate quartile
            if tenant_value <= peer_group_p25:
                quartile = 1
            elif tenant_value <= peer_group_median:
                quartile = 2
            elif tenant_value <= peer_group_p75:
                quartile = 3
            else:
                quartile = 4
        else:
            tenant_value = 0.0
            percentile_rank = None
            quartile = None

        return BenchmarkResponse(
            tenant_id=request.tenant_id,
            metric_name=request.metric_name,
            value=tenant_value,
            peer_group_avg=peer_group_avg,
            peer_group_median=peer_group_median,
            percentile_rank=percentile_rank,
            quartile=quartile,
            comparison_metadata={
                "peer_count": len(benchmarks),
                "p25": peer_group_p25,
                "p75": peer_group_p75,
            },
        )

    async def detect_outliers(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        metric_name: str,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        """
        Detect outliers using IQR method.

        Features implemented:
        - Outlier detection support (Feature #86)
        """
        query = select(Benchmark).where(
            Benchmark.metric_name == metric_name,
            Benchmark.period_start == period_start,
            Benchmark.period_end == period_end,
        )

        result = await db.execute(query)
        benchmarks = result.scalars().all()

        if len(benchmarks) < 4:
            return {"is_outlier": False, "reason": "insufficient_data"}

        values = [b.value for b in benchmarks]
        values.sort()

        q1 = values[len(values) // 4]
        q3 = values[3 * len(values) // 4]
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        tenant_benchmark = next((b for b in benchmarks if b.tenant_id == tenant_id), None)

        if tenant_benchmark:
            is_outlier = tenant_benchmark.value < lower_bound or tenant_benchmark.value > upper_bound
            return {
                "is_outlier": is_outlier,
                "value": tenant_benchmark.value,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "iqr": iqr,
            }

        return {"is_outlier": False, "reason": "no_tenant_data"}


# Singleton instance
benchmark_service = BenchmarkService()
