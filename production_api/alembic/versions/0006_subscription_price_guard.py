"""Persist the Stripe price verified by the webhook; old rows remain unverified.

Compatibility guard: revision 0001_initial builds its schema with current
Base.metadata, so new empty databases already contain stripe_price_id.
Existing databases migrated before SEC-05 do not. Never silently accept a
column with an incompatible type or nullability.
"""
from alembic import op
import sqlalchemy as sa

revision = '0006_subscription_price_guard'
down_revision = '0005_master_profile_fact_ledger'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {col["name"]: col for col in sa.inspect(bind).get_columns("subscriptions")}
    existing = columns.get("stripe_price_id")
    if existing is None:
        op.add_column("subscriptions", sa.Column("stripe_price_id", sa.String(120), nullable=True))
        return
    # A fresh database may already have this column due to dynamic revision 0001.
    # Fail rather than silently trust an incompatible pre-existing definition.
    datatype = existing["type"]
    if not isinstance(datatype, sa.String) or datatype.length != 120 or not existing["nullable"]:
        raise RuntimeError("Incompatible pre-existing subscriptions.stripe_price_id column")


def downgrade():
    # Downgrade from SEC-05 always removes the price authorization field.
    # Follow-up architectural work must freeze revision 0001 independently.
    bind = op.get_bind()
    columns = {col["name"] for col in sa.inspect(bind).get_columns("subscriptions")}
    if "stripe_price_id" in columns:
        op.drop_column("subscriptions", "stripe_price_id")
