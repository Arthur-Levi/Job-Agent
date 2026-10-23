"""Add persistent user-declared evidence assessment history.
Revision ID: 0003_evidence_strength
Revises: 0002_career_graph, 0002_subscription_guard
"""
from alembic import op
import sqlalchemy as sa
revision='0003_evidence_strength'
down_revision=('0002_career_graph','0002_subscription_guard')
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('evidence_assessments',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('evidence_id',sa.Integer(),sa.ForeignKey('evidence.id',ondelete='CASCADE'),nullable=False),
        sa.Column('rubric_version',sa.String(40),nullable=False),
        sa.Column('submission_json',sa.Text(),nullable=False),
        sa.Column('result_json',sa.Text(),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_evidence_assessments_user_id','evidence_assessments',['user_id'])
    op.create_index('ix_evidence_assessments_evidence_id','evidence_assessments',['evidence_id'])

def downgrade():
    op.drop_index('ix_evidence_assessments_evidence_id',table_name='evidence_assessments')
    op.drop_index('ix_evidence_assessments_user_id',table_name='evidence_assessments')
    op.drop_table('evidence_assessments')
