"""Persistent artifact inventories, no source code stored.
Revision ID: 0004_artifact_reviews
Revises: 0003_evidence_strength
"""
from alembic import op
import sqlalchemy as sa
revision='0004_artifact_reviews'
down_revision='0003_evidence_strength'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('artifact_reviews',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('evidence_id',sa.Integer(),sa.ForeignKey('evidence.id',ondelete='CASCADE'),nullable=False),
        sa.Column('review_version',sa.String(40),nullable=False),
        sa.Column('inventory_sha256',sa.String(64),nullable=False),
        sa.Column('result_json',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_artifact_reviews_user_id','artifact_reviews',['user_id'])
    op.create_index('ix_artifact_reviews_evidence_id','artifact_reviews',['evidence_id'])

def downgrade():
    op.drop_index('ix_artifact_reviews_evidence_id',table_name='artifact_reviews')
    op.drop_index('ix_artifact_reviews_user_id',table_name='artifact_reviews')
    op.drop_table('artifact_reviews')
