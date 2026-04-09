from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("ADAPTIX_INSIGHT_APP_NAME", "adaptix-insight")
    app_env: str = os.getenv("ADAPTIX_INSIGHT_ENV", "development")
    dev_secret: str = os.getenv("ADAPTIX_INSIGHT_DEV_SECRET", "adaptix-insight-dev-secret")
    allow_dev_auth: bool = os.getenv("ADAPTIX_INSIGHT_ALLOW_DEV_AUTH", "true").lower() == "true"
    default_tenant_id: str = os.getenv("ADAPTIX_INSIGHT_DEFAULT_TENANT_ID", "00000000-0000-0000-0000-000000000001")
    cors_origins: str = os.getenv("ADAPTIX_INSIGHT_CORS_ORIGINS", "*")


settings = Settings()


def get_settings() -> Settings:
    return settings