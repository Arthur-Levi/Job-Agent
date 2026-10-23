"""Initial production schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
from models import Base
revision='0001_initial'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    Base.metadata.create_all(bind=op.get_bind(),tables=[Base.metadata.tables[n] for n in ('users','sessions','profiles','evidence','jobs','applications','tasks','subscriptions','webhook_events','audit')],checkfirst=True)

def downgrade():
    Base.metadata.drop_all(bind=op.get_bind(),tables=[Base.metadata.tables[n] for n in ('audit','webhook_events','subscriptions','tasks','applications','jobs','evidence','profiles','sessions','users')],checkfirst=True)
