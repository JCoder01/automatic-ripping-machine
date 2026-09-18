"""User drop hash column, password now uses werkzeug's self-contained hash format

Revision ID: 7a4e2b6f9c13
Revises: 3f8a1c9d5b02
Create Date: 2026-09-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a4e2b6f9c13'
down_revision = '3f8a1c9d5b02'
branch_labels = None
depends_on = None


def upgrade():
    # Existing bcrypt hashes can no longer be verified (werkzeug's check_password_hash
    # expects its own format), so reset every user's password to the same "password"
    # default try_add_default_user() already uses for a fresh install - forcing a
    # change on next login is safer than leaving a hash nothing can ever verify.
    from werkzeug.security import generate_password_hash
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE user SET password = :password"),
        {"password": generate_password_hash("password")}
    )
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('password', existing_type=sa.String(length=128),
                             type_=sa.String(length=256))
        batch_op.drop_column('hash')


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('hash', sa.String(length=256), nullable=True))
        batch_op.alter_column('password', existing_type=sa.String(length=256),
                             type_=sa.String(length=128))
