"""Added advanced preprocessing column

Revision ID: 378f0586c3f1
Revises: 
Create Date: 2024-04-03 23:55:05.616929

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '378f0586c3f1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        batch_op.alter_column('pages',
               existing_type=mysql.VARCHAR(length=100),
               type_=sa.String(length=25),
               existing_nullable=True)

    with op.batch_alter_table('embedding_task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('advanced_preprocessing', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('embedding_task', schema=None) as batch_op:
        batch_op.drop_column('advanced_preprocessing')

    with op.batch_alter_table('document_chunks', schema=None) as batch_op:
        batch_op.alter_column('pages',
               existing_type=sa.String(length=25),
               type_=mysql.VARCHAR(length=100),
               existing_nullable=True)

    # ### end Alembic commands ###
