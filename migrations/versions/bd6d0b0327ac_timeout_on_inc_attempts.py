"""timeout on inc attempts

Revision ID: bd6d0b0327ac
Revises: c315c31c1a4f
Create Date: 2023-11-13 09:30:55.024895

"""
from alembic import op
import sqlalchemy as sa

revision = 'bd6d0b0327ac'
down_revision = 'c315c31c1a4f'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('login_attempts', sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column('last_attempt_time', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('last_attempt_time')
        batch_op.drop_column('login_attempts')
