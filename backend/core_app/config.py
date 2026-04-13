"""Configuration management for Adaptix Insight."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Adaptix Insight application settings."""

    model_config = SettingsConfigDict(env_prefix="ADAPTIX_INSIGHT_", env_file=".env", extra="ignore")

    # Application
    app_name: str = Field(default="adaptix-insight", description="Application name")
    app_env: str = Field(default="development", description="Environment (development, staging, production)")
    log_level: str = Field(default="INFO", description="Logging level")

    # Authentication & Security
    dev_secret: str = Field(default="adaptix-insight-dev-secret", description="Dev authentication secret")
    allow_dev_auth: bool = Field(default=True, description="Allow development authentication")
    default_tenant_id: str = Field(
        default="00000000-0000-0000-0000-000000000001", description="Default tenant ID"
    )

    # CORS
    cors_origins: str = Field(default="*", description="Comma-separated CORS origins")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://insight:insight@localhost:5432/adaptix_insight",
        description="Async PostgreSQL database URL",
    )
    database_url_sync: str = Field(
        default="postgresql://insight:insight@localhost:5432/adaptix_insight",
        description="Sync PostgreSQL database URL for migrations",
    )
    database_pool_size: int = Field(default=20, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, description="Database max overflow connections")

    # Observability
    enable_tracing: bool = Field(default=False, description="Enable OpenTelemetry tracing")
    trace_exporter_endpoint: str | None = Field(default=None, description="OTLP trace exporter endpoint")

    # Data Retention
    raw_data_retention_days: int = Field(default=730, description="Raw analytics data retention (2 years)")
    aggregated_data_retention_days: int = Field(default=2555, description="Aggregated data retention (7 years)")
    audit_log_retention_days: int = Field(default=2555, description="Audit log retention (7 years)")

    # Feature Flags
    enable_real_time_aggregation: bool = Field(default=False, description="Enable near-real-time aggregation")
    enable_ai_insights: bool = Field(default=False, description="Enable AI-assisted insight generation")

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.app_env.lower() == "development"


settings = Settings()


def get_settings() -> Settings:
    """Get application settings instance."""
    return settings