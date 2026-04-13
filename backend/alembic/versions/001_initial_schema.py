"""Initial schema with fixed metadata columns

Revision ID: 001
Revises:
Create Date: 2026-04-13 21:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create analytics_events table
    op.create_table(
        'analytics_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('source_domain', sa.String(50), nullable=False, index=True),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('correlation_id', sa.String(255), index=True),
        sa.Column('idempotency_key', sa.String(255), unique=True, index=True),
        sa.Column('payload', postgresql.JSON, nullable=False),
        sa.Column('event_metadata', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_analytics_events_tenant_event_time', 'analytics_events', ['tenant_id', 'event_timestamp'])
    op.create_index('ix_analytics_events_source_event_time', 'analytics_events', ['source_domain', 'event_timestamp'])

    # Create ingestion_audit_logs table
    op.create_table(
        'ingestion_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), index=True),
        sa.Column('source_domain', sa.String(50), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text),
        sa.Column('audit_metadata', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, index=True),
    )

    # Create domain_rollups table
    op.create_table(
        'domain_rollups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('source_domain', sa.String(50), nullable=False, index=True),
        sa.Column('aggregation_level', sa.String(20), nullable=False, index=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metrics', postgresql.JSON, nullable=False),
        sa.Column('event_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_domain_rollups_unique', 'domain_rollups', ['tenant_id', 'source_domain', 'aggregation_level', 'period_start'], unique=True)

    # Create tenant_rollups table
    op.create_table(
        'tenant_rollups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('aggregation_level', sa.String(20), nullable=False, index=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metrics', postgresql.JSON, nullable=False),
        sa.Column('domain_breakdown', postgresql.JSON, nullable=False),
        sa.Column('event_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_tenant_rollups_unique', 'tenant_rollups', ['tenant_id', 'aggregation_level', 'period_start'], unique=True)

    # Create kpi_definitions table
    op.create_table(
        'kpi_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('kpi_code', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('kpi_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('formula', sa.Text, nullable=False),
        sa.Column('formula_version', sa.Integer, nullable=False, server_default='1'),
        sa.Column('source_domains', postgresql.JSON, nullable=False),
        sa.Column('unit', sa.String(50)),
        sa.Column('threshold_warning', sa.Float),
        sa.Column('threshold_critical', sa.Float),
        sa.Column('target_value', sa.Float),
        sa.Column('owner', sa.String(100)),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )

    # Create kpi_values table
    op.create_table(
        'kpi_values',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('kpi_code', sa.String(100), nullable=False, index=True),
        sa.Column('aggregation_level', sa.String(20), nullable=False, index=True),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('status', sa.String(20)),
        sa.Column('trend_direction', sa.String(20)),
        sa.Column('delta_from_previous', sa.Float),
        sa.Column('delta_from_target', sa.Float),
        sa.Column('kpi_metadata', postgresql.JSON),
        sa.Column('quality_score', sa.Float),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )
    op.create_index('ix_kpi_values_unique', 'kpi_values', ['tenant_id', 'kpi_code', 'aggregation_level', 'period_start'], unique=True)

    # Create benchmarks table
    op.create_table(
        'benchmarks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('benchmark_type', sa.String(50), nullable=False, index=True),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('peer_group_avg', sa.Float),
        sa.Column('peer_group_median', sa.Float),
        sa.Column('peer_group_p25', sa.Float),
        sa.Column('peer_group_p75', sa.Float),
        sa.Column('percentile_rank', sa.Float),
        sa.Column('quartile', sa.Integer),
        sa.Column('comparison_metadata', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )

    # Create report_definitions table
    op.create_table(
        'report_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('report_name', sa.String(255), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False, index=True),
        sa.Column('description', sa.Text),
        sa.Column('parameters', postgresql.JSON, nullable=False),
        sa.Column('schedule_config', postgresql.JSON),
        sa.Column('export_formats', postgresql.JSON, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    )

    # Create data_quality_metrics table
    op.create_table(
        'data_quality_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('source_domain', sa.String(50), nullable=False, index=True),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('value', sa.Float, nullable=False),
        sa.Column('threshold', sa.Float),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('last_data_timestamp', sa.DateTime(timezone=True)),
        sa.Column('completeness_score', sa.Float),
        sa.Column('warnings', postgresql.JSON),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('data_quality_metrics')
    op.drop_table('report_definitions')
    op.drop_table('benchmarks')
    op.drop_table('kpi_values')
    op.drop_table('kpi_definitions')
    op.drop_table('tenant_rollups')
    op.drop_table('domain_rollups')
    op.drop_table('ingestion_audit_logs')
    op.drop_table('analytics_events')
