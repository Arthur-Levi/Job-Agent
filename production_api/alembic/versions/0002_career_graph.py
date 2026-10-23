"""Persistent evidence graph, snapshots and outcomes.

Revision ID: 0002_career_graph
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa
revision='0002_career_graph'
down_revision='0001_initial'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('evidence_links',
        sa.Column('id',sa.Integer(),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('evidence_id',sa.Integer(),sa.ForeignKey('evidence.id',ondelete='CASCADE'),nullable=False),
        sa.Column('requirement',sa.String(160),nullable=False),sa.Column('relation',sa.String(30),nullable=False),
        sa.Column('rationale',sa.Text(),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('user_id','evidence_id','requirement',name='uq_graph_edge'))
    op.create_index('ix_evidence_links_user_id','evidence_links',['user_id'])
    op.create_index('ix_evidence_links_evidence_id','evidence_links',['evidence_id'])
    op.create_table('career_snapshots',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('metrics_json',sa.Text(),nullable=False),sa.Column('recommendations_json',sa.Text(),nullable=False),
        sa.Column('explanation_json',sa.Text(),nullable=False))
    op.create_index('ix_career_snapshots_user_id','career_snapshots',['user_id'])
    op.create_table('career_outcomes',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('kind',sa.String(30),nullable=False),sa.Column('description',sa.Text(),nullable=False),
        sa.Column('job_id',sa.Integer(),sa.ForeignKey('jobs.id',ondelete='SET NULL')),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_career_outcomes_user_id','career_outcomes',['user_id'])

def downgrade():
    op.drop_table('career_outcomes')
    op.drop_table('career_snapshots')
    op.drop_table('evidence_links')
