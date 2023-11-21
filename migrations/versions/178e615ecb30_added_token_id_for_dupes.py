"""added token id for dupes

Revision ID: 178e615ecb30
Revises: 5024978f0910
Create Date: 2023-11-19 00:32:53.317198

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '178e615ecb30'
down_revision = '5024978f0910'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.add_column(sa.Column('api_key_token', sa.String(length=36), nullable=False))
        batch_op.create_unique_constraint(None, ['api_key_token'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user_api_keys', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='unique')
        batch_op.drop_column('api_key_token')

    # ### end Alembic commands ###
