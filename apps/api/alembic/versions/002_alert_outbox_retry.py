"""alert outbox retry fields

Revision ID: 002_alert_outbox_retry
Revises: 001_initial_schema
Create Date: 2026-08-13 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '002_alert_outbox_retry'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('alert_deliveries', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('alert_deliveries', sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'))
    op.add_column('alert_deliveries', sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('alert_deliveries', sa.Column('idempotency_key', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_alert_deliveries_idempotency_key'), 'alert_deliveries', ['idempotency_key'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_alert_deliveries_idempotency_key'), table_name='alert_deliveries')
    op.drop_column('alert_deliveries', 'idempotency_key')
    op.drop_column('alert_deliveries', 'next_retry_at')
    op.drop_column('alert_deliveries', 'max_retries')
    op.drop_column('alert_deliveries', 'retry_count')
