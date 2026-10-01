"""Job add iso_path, for the tolerant rip-via-ISO retry

Revision ID: c1a9f3d7e2b4
Revises: 8b2f4e9a1c67
Create Date: 2026-09-24

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1a9f3d7e2b4'
down_revision = '8b2f4e9a1c67'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('iso_path', sa.String(length=256), nullable=True))


def downgrade():
    with op.batch_alter_table('job', schema=None) as batch_op:
        batch_op.drop_column('iso_path')
