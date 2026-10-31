"""Persist the Stripe price verified by the webhook; old rows remain unverified."""
from alembic import op
import sqlalchemy as sa

revision = '0006_subscription_price_guard'
down_revision = '0005_master_profile_fact_ledger'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('subscriptions', sa.Column('stripe_price_id', sa.String(120), nullable=True))

def downgrade():
    op.drop_column('subscriptions', 'stripe_price_id')
