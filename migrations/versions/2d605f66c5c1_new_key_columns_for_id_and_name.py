"""new key columns for id and name

Revision ID: 2d605f66c5c1
Revises: 0f4554302036
Create Date: 2023-11-18 22:28:28.065139

"""
from alembic import op
import sqlalchemy as sa

revision = '2d605f66c5c1'
down_revision = '0f4554302036'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.add_column(sa.Column('nickname', sa.String(length=25), nullable=False))
        batch_op.add_column(
            sa.Column('identifier', sa.String(length=6), nullable=False))


def downgrade():
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.drop_column('identifier')
        batch_op.drop_column('nickname')
