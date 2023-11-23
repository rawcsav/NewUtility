"""user change timeout

Revision ID: c05089cb8d86
Revises: bd6d0b0327ac
Create Date: 2023-11-13 12:26:28.878313

"""
from alembic import op
import sqlalchemy as sa

revision = 'c05089cb8d86'
down_revision = 'bd6d0b0327ac'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('last_username_change', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_username_change')
