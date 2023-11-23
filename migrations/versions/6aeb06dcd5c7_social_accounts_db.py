"""social accounts db

Revision ID: 6aeb06dcd5c7
Revises: 6d2dab687e28
Create Date: 2023-11-14 09:14:29.824341

"""
from alembic import op
import sqlalchemy as sa

revision = '6aeb06dcd5c7'
down_revision = '6d2dab687e28'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('login_method', sa.String(length=10), nullable=False))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('login_method')
