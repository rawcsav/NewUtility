"""removed unneeded columns

Revision ID: 0f4554302036
Revises: 6aeb06dcd5c7
Create Date: 2023-11-18 20:50:42.616331

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '0f4554302036'
down_revision = '6aeb06dcd5c7'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.drop_column('models')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('openai_api_key')


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('openai_api_key', mysql.VARCHAR(length=255), nullable=True))

    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('models', mysql.VARCHAR(length=255), nullable=True))
