"""Change encrypted_api_key to binary type

Revision ID: 5024978f0910
Revises: 2d605f66c5c1
Create Date: 2023-11-19 00:24:24.230719

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '5024978f0910'
down_revision = '2d605f66c5c1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.alter_column('encrypted_api_key',
                              existing_type=mysql.VARCHAR(length=255),
                              type_=sa.BLOB(),
                              existing_nullable=False)


def downgrade():
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.alter_column('encrypted_api_key',
                              existing_type=sa.BLOB(),
                              type_=mysql.VARCHAR(length=255),
                              existing_nullable=False)
