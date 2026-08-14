"""add audit logs composite index

Revision ID: 003_add_telemetry_indexes
Revises: 002_alert_outbox_retry
Create Date: 2026-08-14 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '003_add_telemetry_indexes'
down_revision = '002_alert_outbox_retry'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_index('ix_audit_logs_project_created', 'audit_logs', ['project_id', 'created_at'], unique=False)

def downgrade() -> None:
    op.drop_index('ix_audit_logs_project_created', table_name='audit_logs')
