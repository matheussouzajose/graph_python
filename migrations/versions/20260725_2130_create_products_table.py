"""create products table

Revision ID: f1a2b3c4d5e7
Revises: 9d8274569d7c
Create Date: 2026-07-25 21:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e7"
down_revision: str | None = "9d8274569d7c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("integration_id", sa.Uuid(), nullable=False),
        sa.Column("external_product_id", sa.String(length=255), nullable=False),
        sa.Column("external_company_id", sa.Uuid(), nullable=False),
        sa.Column("integration_product_id", sa.String(length=255), nullable=True),
        sa.Column("code", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=1024), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("full_description", sa.String(), nullable=True),
        sa.Column("composition", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("promotion", sa.Boolean(), nullable=False),
        sa.Column("price_promotional", sa.Float(), nullable=True),
        sa.Column("slug", sa.String(length=1024), nullable=True),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("length", sa.Float(), nullable=True),
        sa.Column("external_created_at", sa.DateTime(), nullable=True),
        sa.Column("external_updated_at", sa.DateTime(), nullable=True),
        sa.Column("release_at", sa.DateTime(), nullable=True),
        sa.Column("order_date", sa.DateTime(), nullable=True),
        sa.Column("brand", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("negotiations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sizes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("colors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("stocks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("media", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["integration_id"],
            ["integrations.id"],
            name="fk_products_integration_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "integration_id", "external_product_id", name="uq_products_integration_external_id"
        ),
    )
    op.create_index(
        "ix_products_integration_updated_at",
        "products",
        ["integration_id", "external_updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_products_integration_updated_at", table_name="products")
    op.drop_table("products")
