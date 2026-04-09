from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from core_app.api.dependencies import CurrentUser, get_current_user

router = APIRouter(tags=["commercial"])


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@router.get("/api/v1/roi-funnel/conversion-kpis")
async def conversion_kpis(_current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"total_events": 0, "total_proposals": 0, "active_subscriptions": 0, "proposal_to_paid_conversion_pct": 0.0, "as_of": _now_iso()}


@router.get("/api/v1/roi-funnel/conversion-funnel")
async def conversion_funnel(_current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"funnel": [], "total_events": 0}


@router.get("/api/v1/roi-funnel/revenue-pipeline")
async def revenue_pipeline(_current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"pending_pipeline_cents": 0, "active_mrr_cents": 0, "pipeline_to_mrr_ratio": 0.0, "as_of": _now_iso()}


@router.get("/api/v1/roi-funnel/subscription-lifecycle")
async def subscription_lifecycle(_current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"lifecycle": {}, "total": 0, "as_of": _now_iso()}


@router.get("/api/v1/billing-command/payer-mix")
async def payer_mix(_current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"payer_mix": [], "total_claims": 0}


@router.get("/api/v1/billing-command/stripe-reconciliation")
async def stripe_reconciliation(_current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"active_subscriptions": 0, "past_due_subscriptions": 0, "mrr_cents": 0, "as_of": _now_iso()}


@router.get("/api/v1/billing-command/churn-risk")
async def churn_risk(_current_user: CurrentUser = Depends(get_current_user)) -> dict:
    return {"at_risk_subscriptions": [], "count": 0}
