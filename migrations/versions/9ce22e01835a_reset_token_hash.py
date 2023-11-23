"""reset token hash

Revision ID: 9ce22e01835a
Revises: e7be8d20ee39
Create Date: 2023-11-20 23:23:30.025182

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '9ce22e01835a'
down_revision = 'e7be8d20ee39'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('reset_token_hash', sa.String(length=255), nullable=True))
        batch_op.alter_column('username',
                              existing_type=mysql.VARCHAR(length=50),
                              type_=sa.String(length=20),
                              existing_nullable=False)
        batch_op.alter_column('confirmation_code',
                              existing_type=mysql.VARCHAR(length=100),
                              type_=sa.String(length=6),
                              existing_nullable=True)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('confirmation_code',
                              existing_type=sa.String(length=6),
                              type_=mysql.VARCHAR(length=100),
                              existing_nullable=True)
        batch_op.alter_column('username',
                              existing_type=sa.String(length=20),
                              type_=mysql.VARCHAR(length=50),
                              existing_nullable=False)
        batch_op.drop_column('reset_token_hash')
