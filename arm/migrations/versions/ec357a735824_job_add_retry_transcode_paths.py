"""Job add raw_path and transcode_out_path, for transcode-only retry

Revision ID: ec357a735824
Revises: edf2272c0a9d
Create Date: 2026-09-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ec357a735824'
down_revision = 'edf2272c0a9d'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('raw_path', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('transcode_out_path', sa.String(length=256), nullable=True))


def downgrade():
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.drop_column('transcode_out_path')
        batch_op.drop_column('raw_path')
