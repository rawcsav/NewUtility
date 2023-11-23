"""added color mode to user

Revision ID: e7be8d20ee39
Revises: 16644d889d2c
Create Date: 2023-11-19 22:18:26.270609

"""
from alembic import op
import sqlalchemy as sa

revision = 'e7be8d20ee39'
down_revision = '16644d889d2c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('color_mode', sa.String(length=10), nullable=False))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('color_mode')
