"""img db columns

Revision ID: 91f55d4f699f
Revises: 
Create Date: 2024-01-07 22:29:13.382355

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91f55d4f699f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('generated_images', schema=None) as batch_op:
        batch_op.add_column(sa.Column('size', sa.String(length=50), nullable=False))
        batch_op.add_column(sa.Column('quality', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('style', sa.String(length=50), nullable=True))

    with op.batch_alter_table('message_chunk_association', schema=None) as batch_op:
        batch_op.drop_constraint('message_chunk_association_ibfk_2', type_='foreignkey')
        batch_op.create_foreign_key(None, 'document_chunks', ['chunk_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('message_chunk_association', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key('message_chunk_association_ibfk_2', 'document_chunks', ['chunk_id'], ['id'], ondelete='CASCADE')

    with op.batch_alter_table('generated_images', schema=None) as batch_op:
        batch_op.drop_column('style')
        batch_op.drop_column('quality')
        batch_op.drop_column('size')

    # ### end Alembic commands ###
