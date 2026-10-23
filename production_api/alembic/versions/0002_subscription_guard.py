"""Production billing lookup indexes.

Revision ID: 0002_subscription_guard
Revises: 0001_initial
"""
from alembic import op
revision='0002_subscription_guard'
down_revision='0001_initial'
branch_labels=None
depends_on=None

def upgrade():
    op.create_index('ix_webhook_events_processed_at','webhook_events',['processed_at'])
    op.create_index('ix_audit_created_at','audit',['created_at'])

def downgrade():
    op.drop_index('ix_audit_created_at',table_name='audit')
    op.drop_index('ix_webhook_events_processed_at',table_name='webhook_events')
