"""add agent category

Revision ID: 7c1d2e3f4a5b
Revises: 258cfe408daa
Create Date: 2026-07-26 00:01:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7c1d2e3f4a5b'
down_revision: str | None = '258cfe408daa'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('agents', sa.Column('category', sa.String(length=100), nullable=True))
    op.add_column('agents', sa.Column('tags', sa.ARRAY(sa.String()), nullable=False, server_default='{}'))
    op.add_column('agents', sa.Column('skills', sa.ARRAY(sa.String()), nullable=False, server_default='{}'))
    op.add_column('agents', sa.Column('image_size', sa.String(length=20), nullable=True))
    op.add_column('agents', sa.Column('image_quality', sa.String(length=20), nullable=True))
    op.add_column('agents', sa.Column('image_format', sa.String(length=10), nullable=True))
    op.alter_column('agents', 'tags', server_default=None)
    op.alter_column('agents', 'skills', server_default=None)
    op.create_index('ix_agents_category', 'agents', ['category'])


def downgrade() -> None:
    op.drop_index('ix_agents_category', table_name='agents')
    op.drop_column('agents', 'image_format')
    op.drop_column('agents', 'image_quality')
    op.drop_column('agents', 'image_size')
    op.drop_column('agents', 'skills')
    op.drop_column('agents', 'tags')
    op.drop_column('agents', 'category')
