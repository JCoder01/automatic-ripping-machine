"""Config add MOVIE_MIN_LENGTH and SHOW_MIN_LENGTH

Revision ID: 8b2f4e9a1c67
Revises: 7a4e2b6f9c13
Create Date: 2026-09-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8b2f4e9a1c67'
down_revision = '7a4e2b6f9c13'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('MOVIE_MIN_LENGTH', sa.String(length=6), nullable=True))
        batch_op.add_column(sa.Column('SHOW_MIN_LENGTH', sa.String(length=6), nullable=True))


def downgrade():
    with op.batch_alter_table('config', schema=None) as batch_op:
        batch_op.drop_column('SHOW_MIN_LENGTH')
        batch_op.drop_column('MOVIE_MIN_LENGTH')
