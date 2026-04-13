"""Benchmark API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db import get_db
from core_app.logging_config import get_logger
from core_app.schemas import BenchmarkRequest, BenchmarkResponse
from core_app.services.benchmark_service import benchmark_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/insight/benchmark", tags=["Benchmarking"])


@router.post("/compare", response_model=BenchmarkResponse)
async def compare_benchmark(
    request: BenchmarkRequest,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkResponse:
    """
    Compare metric to peer group benchmarks.

    Features implemented:
    - Benchmark comparison engine (Feature #71)
    - Peer-group benchmark support (Feature #72)
    - Percentile ranking support (Feature #85)
    - Performance quartile ranking (Feature #84)
    - Outlier detection support (Feature #86)
    """
    try:
        return await benchmark_service.compare_to_peer_group(db, request)
    except Exception as e:
        logger.error("benchmark_comparison_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare benchmarks: {str(e)}",
        )
