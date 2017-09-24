"""add announce table

Revision ID: 05a34cc8ab88
Revises: 00a9ac502dd3
Create Date: 2017-09-21 20:38:45.744858

"""

# revision identifiers, used by Alembic.
revision = '05a34cc8ab88'
down_revision = '00a9ac502dd3'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('announce',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('url', sa.TEXT(), nullable=True),
    sa.Column('image_url', sa.TEXT(), nullable=True),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('sort_order', sa.Integer(), nullable=True),
    sa.Column('start_time', sa.TIMESTAMP(), nullable=False),
    sa.Column('end_time', sa.TIMESTAMP(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('announce')
    # ### end Alembic commands ###
