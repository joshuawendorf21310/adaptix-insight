"""Tests for benchmark service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models import Benchmark
from core_app.schemas import BenchmarkRequest
from core_app.services.benchmark_service import benchmark_service


@pytest.mark.asyncio
async def test_peer_group_comparison(db_session: AsyncSession):
    """
    Test peer-group benchmark comparison.

    Features tested:
    - Benchmark comparison engine (Feature #71)
    - Peer-group benchmark support (Feature #72)
    - Percentile ranking support (Feature #85)
    - Performance quartile ranking (Feature #84)
    """
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create benchmark data for multiple tenants
    tenant_ids = [uuid.uuid4() for _ in range(10)]
    values = [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0]

    for tenant_id, value in zip(tenant_ids, values):
        benchmark = Benchmark(
            tenant_id=tenant_id,
            benchmark_type="peer_group",
            metric_name="response_time",
            period_start=now,
            period_end=period_end,
            value=value,
        )
        db_session.add(benchmark)
    await db_session.flush()

    # Compare tenant in the middle (value=9.0)
    request = BenchmarkRequest(
        tenant_id=tenant_ids[4],  # 5th tenant with value 9.0
        metric_name="response_time",
        period_start=now,
        period_end=period_end,
        comparison_type="peer_group",
    )

    result = await benchmark_service.compare_to_peer_group(db_session, request)

    assert result.tenant_id == tenant_ids[4]
    assert result.metric_name == "response_time"
    assert result.value == 9.0
    assert result.peer_group_avg is not None
    assert result.peer_group_median is not None
    assert result.percentile_rank is not None
    assert result.quartile is not None
    assert 1 <= result.quartile <= 4


@pytest.mark.asyncio
async def test_quartile_ranking(db_session: AsyncSession):
    """
    Test quartile ranking calculation.

    Features tested:
    - Performance quartile ranking (Feature #84)
    """
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create benchmarks with known quartile distribution
    tenant_ids = [uuid.uuid4() for _ in range(20)]
    values = list(range(1, 21))  # 1 to 20

    for tenant_id, value in zip(tenant_ids, values):
        benchmark = Benchmark(
            tenant_id=tenant_id,
            benchmark_type="peer_group",
            metric_name="test_metric",
            period_start=now,
            period_end=period_end,
            value=float(value),
        )
        db_session.add(benchmark)
    await db_session.flush()

    # Test tenant in Q1 (value=3)
    request_q1 = BenchmarkRequest(
        tenant_id=tenant_ids[2],
        metric_name="test_metric",
        period_start=now,
        period_end=period_end,
        comparison_type="peer_group",
    )
    result_q1 = await benchmark_service.compare_to_peer_group(db_session, request_q1)
    assert result_q1.quartile == 1

    # Test tenant in Q4 (value=18)
    request_q4 = BenchmarkRequest(
        tenant_id=tenant_ids[17],
        metric_name="test_metric",
        period_start=now,
        period_end=period_end,
        comparison_type="peer_group",
    )
    result_q4 = await benchmark_service.compare_to_peer_group(db_session, request_q4)
    assert result_q4.quartile == 4


@pytest.mark.asyncio
async def test_outlier_detection(db_session: AsyncSession):
    """
    Test outlier detection using IQR method.

    Features tested:
    - Outlier detection support (Feature #86)
    """
    tenant_id = uuid.uuid4()
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create normal distribution of benchmarks
    normal_values = [8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0]
    for i, value in enumerate(normal_values):
        benchmark = Benchmark(
            tenant_id=uuid.uuid4() if i > 0 else tenant_id,
            benchmark_type="peer_group",
            metric_name="test_metric",
            period_start=now,
            period_end=period_end,
            value=value,
        )
        db_session.add(benchmark)

    # Add an outlier (extremely high value)
    outlier_tenant = uuid.uuid4()
    outlier_benchmark = Benchmark(
        tenant_id=outlier_tenant,
        benchmark_type="peer_group",
        metric_name="test_metric",
        period_start=now,
        period_end=period_end,
        value=50.0,  # Clear outlier
    )
    db_session.add(outlier_benchmark)
    await db_session.flush()

    # Detect outlier
    outlier_result = await benchmark_service.detect_outliers(
        db=db_session,
        tenant_id=outlier_tenant,
        metric_name="test_metric",
        period_start=now,
        period_end=period_end,
    )

    assert outlier_result["is_outlier"] is True
    assert outlier_result["value"] == 50.0

    # Check normal value is not an outlier
    normal_result = await benchmark_service.detect_outliers(
        db=db_session,
        tenant_id=tenant_id,
        metric_name="test_metric",
        period_start=now,
        period_end=period_end,
    )

    assert normal_result["is_outlier"] is False


@pytest.mark.asyncio
async def test_percentile_ranking(db_session: AsyncSession):
    """
    Test percentile ranking calculation.

    Features tested:
    - Percentile ranking support (Feature #85)
    """
    now = datetime.now()
    period_end = now + timedelta(days=30)

    # Create 100 benchmarks for precise percentile testing
    tenant_ids = [uuid.uuid4() for _ in range(100)]
    values = list(range(1, 101))  # 1 to 100

    for tenant_id, value in zip(tenant_ids, values):
        benchmark = Benchmark(
            tenant_id=tenant_id,
            benchmark_type="peer_group",
            metric_name="percentile_test",
            period_start=now,
            period_end=period_end,
            value=float(value),
        )
        db_session.add(benchmark)
    await db_session.flush()

    # Test 90th percentile (value=90)
    request = BenchmarkRequest(
        tenant_id=tenant_ids[89],
        metric_name="percentile_test",
        period_start=now,
        period_end=period_end,
        comparison_type="peer_group",
    )
    result = await benchmark_service.compare_to_peer_group(db_session, request)

    # Should be approximately 89th percentile
    assert result.percentile_rank is not None
    assert 85.0 <= result.percentile_rank <= 92.0  # Allow some tolerance
