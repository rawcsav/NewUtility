"""added token id for dupes

Revision ID: 16644d889d2c
Revises: 178e615ecb30
Create Date: 2023-11-19 00:35:59.752397

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '16644d889d2c'
down_revision = '178e615ecb30'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.alter_column('api_key_token',
                              existing_type=mysql.VARCHAR(length=36),
                              type_=sa.String(length=64),
                              existing_nullable=False)


def downgrade():
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.alter_column('api_key_token',
                              existing_type=sa.String(length=64),
                              type_=mysql.VARCHAR(length=36),
                              existing_nullable=False)
