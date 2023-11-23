"""key models in db

Revision ID: 6d2dab687e28
Revises: c05089cb8d86
Create Date: 2023-11-13 13:06:19.712515

"""
from alembic import op
import sqlalchemy as sa

revision = '6d2dab687e28'
down_revision = 'c05089cb8d86'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.add_column(sa.Column('models', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.drop_column('models')
