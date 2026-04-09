from __future__ import annotations

import os

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["observability"])

_SCRAPE_TOKEN = os.getenv("METRICS_SCRAPE_TOKEN", "")


def _verify_scrape_token(authorization: str | None = Header(default=None)) -> None:
    if not _SCRAPE_TOKEN:
        return
    if authorization != f"Bearer {_SCRAPE_TOKEN}":
        raise HTTPException(status_code=403, detail="Invalid scrape token")


@router.get("/metrics", response_class=PlainTextResponse, dependencies=[Depends(_verify_scrape_token)])
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)
