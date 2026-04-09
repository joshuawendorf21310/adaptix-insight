from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core_app.api.adaptix_insight_router import router as adaptix_insight_router
from core_app.api.auth_router import router as auth_router
from core_app.api.commercial_router import router as commercial_router
from core_app.api.founder_router import router as founder_router
from core_app.api.founder_surface_router import router as founder_surface_router
from core_app.api.health_router import router as health_router
from core_app.api.metrics_router import router as metrics_router
from core_app.api.system_health_shell_router import router as system_health_router
from core_app.config import settings

app = FastAPI(title="Adaptix Insight", version="0.1.0")

origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(commercial_router)
app.include_router(founder_router)
app.include_router(founder_surface_router)
app.include_router(system_health_router)
app.include_router(metrics_router)
app.include_router(adaptix_insight_router)