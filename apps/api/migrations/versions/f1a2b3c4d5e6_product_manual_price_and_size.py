"""product manual price, size, photo

Revision ID: f1a2b3c4d5e6
Revises: d3f8a1c29b4e
Create Date: 2026-10-01 19:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'f1a2b3c4d5e6'
down_revision: str | None = 'd3f8a1c29b4e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('products', sa.Column('manual_price', sa.Numeric(10, 2), nullable=True))
    op.add_column('products', sa.Column('size', sa.String(length=100), nullable=True))
    op.add_column('products', sa.Column('photo_url', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'photo_url')
    op.drop_column('products', 'size')
    op.drop_column('products', 'manual_price')
