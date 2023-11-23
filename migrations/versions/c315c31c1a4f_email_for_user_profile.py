"""email for user profile

Revision ID: c315c31c1a4f
Revises: 
Create Date: 2023-11-13 08:43:23.247004

"""
from alembic import op
import sqlalchemy as sa

revision = 'c315c31c1a4f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_confirmed', sa.Boolean(), nullable=False))
        batch_op.add_column(
            sa.Column('confirmation_code', sa.String(length=100), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('confirmation_code')
        batch_op.drop_column('email_confirmed')
