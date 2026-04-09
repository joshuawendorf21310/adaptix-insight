"""Adaptix Insight alias router."""

from core_app.api.adaptix_domain_router_common import build_adaptix_domain_router

router = build_adaptix_domain_router(
    module="insight",
    tag="Adaptix Insight",
    prefix="/api/insight",
    legacy_routes=["/api/v1/founder", "/api/v1/system-health", "/metrics"],
    legacy_modules=["founder_router", "system_health_router", "metrics_router"],
)