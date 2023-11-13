from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9029b07ec6fe'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Drop the foreign key constraint
    op.drop_constraint('fk_constraint_name', 'users', type_='foreignkey')

    # (Perform other operations here, if needed)

    # Recreate the foreign key constraint
    op.create_foreign_key('fk_constraint_name', 'users', 'user_api_keys',
                          ['foreign_key_column'], ['referenced_column'])


def downgrade():
    # Drop the recreated foreign key constraint
    op.drop_constraint('fk_constraint_name', 'users', type_='foreignkey')

    # (Perform other operations here, if needed)

    # Recreate the original foreign key constraint
    op.create_foreign_key('fk_constraint_name', 'users', 'user_api_keys',
                          ['foreign_key_column'], ['referenced_column'])
