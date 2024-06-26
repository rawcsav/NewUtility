"""added filename to audio jobs

Revision ID: 772940d8d47a
Revises: 759d61cc626a
Create Date: 2024-04-09 12:28:10.247161

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '772940d8d47a'
down_revision = '759d61cc626a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('transcription_task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('original_filename', sa.String(length=255), nullable=True))

    with op.batch_alter_table('translation_task', schema=None) as batch_op:
        batch_op.add_column(sa.Column('original_filename', sa.String(length=255), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('translation_task', schema=None) as batch_op:
        batch_op.drop_column('original_filename')

    with op.batch_alter_table('transcription_task', schema=None) as batch_op:
        batch_op.drop_column('original_filename')

    # ### end Alembic commands ###
