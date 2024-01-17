"""Add roles and user-role relationship

Revision ID: 422e2ca2078b
Revises: 0a8a3fab7398
Create Date: 2024-01-13 09:38:29.979808

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '422e2ca2078b'
down_revision = '0a8a3fab7398'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('role', schema=None) as batch_op:
        batch_op.drop_column('permissions')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('role', schema=None) as batch_op:
        batch_op.add_column(sa.Column('permissions', mysql.INTEGER(), autoincrement=False, nullable=True))

    # ### end Alembic commands ###