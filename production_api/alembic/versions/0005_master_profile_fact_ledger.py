"""Structured master profile and append-only fact ledger."""
from alembic import op
import sqlalchemy as sa
revision='0005_master_profile_fact_ledger'
down_revision='0004_artifact_reviews'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('master_profile_items',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('category',sa.String(30),nullable=False),sa.Column('title',sa.String(180),nullable=False),
        sa.Column('organization',sa.String(180),nullable=False),sa.Column('start_date',sa.String(10),nullable=False),
        sa.Column('end_date',sa.String(10),nullable=False),sa.Column('description',sa.Text(),nullable=False),
        sa.Column('source_evidence_id',sa.Integer(),sa.ForeignKey('evidence.id',ondelete='SET NULL')),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_master_profile_items_user_id','master_profile_items',['user_id'])
    op.create_table('career_facts',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('subject',sa.String(180),nullable=False),sa.Column('predicate',sa.String(80),nullable=False),
        sa.Column('value',sa.Text(),nullable=False),sa.Column('source_type',sa.String(40),nullable=False),
        sa.Column('source_reference',sa.String(300),nullable=False),sa.Column('verification',sa.String(40),nullable=False),
        sa.Column('status',sa.String(20),nullable=False),
        sa.Column('supersedes_id',sa.Integer(),sa.ForeignKey('career_facts.id',ondelete='SET NULL')),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_career_facts_user_id','career_facts',['user_id'])

def downgrade():
    op.drop_index('ix_career_facts_user_id',table_name='career_facts')
    op.drop_table('career_facts')
    op.drop_index('ix_master_profile_items_user_id',table_name='master_profile_items')
    op.drop_table('master_profile_items')
