"""img table

Revision ID: 9dc9ae99d316
Revises: 9ce22e01835a
Create Date: 2023-11-21 10:43:36.292617

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision = '9dc9ae99d316'
down_revision = '9ce22e01835a'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('user_models')


def downgrade():
    op.create_table('user_models',
                    sa.Column('id', mysql.INTEGER(), autoincrement=True,
                              nullable=False),
                    sa.Column('user_id', mysql.INTEGER(), autoincrement=False,
                              nullable=True),
                    sa.Column('model_name', mysql.VARCHAR(length=50), nullable=False),
                    sa.Column('created_at', mysql.DATETIME(),
                              server_default=sa.text('CURRENT_TIMESTAMP'),
                              nullable=True),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                            name='user_models_ibfk_1'),
                    sa.PrimaryKeyConstraint('id'),
                    mysql_default_charset='utf8mb3',
                    mysql_engine='InnoDB'
                    )
