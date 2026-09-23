"""Config add EMBY_SSL

Revision ID: 3f8a1c9d5b02
Revises: ec357a735824
Create Date: 2026-09-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3f8a1c9d5b02'
down_revision = 'ec357a735824'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('EMBY_SSL', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('config', schema=None) as batch_op:
        batch_op.drop_column('EMBY_SSL')
