"""product photo_urls (replaces single photo_url)

Revision ID: a7c3e9f12b4d
Revises: f1a2b3c4d5e6
Create Date: 2026-10-02 12:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a7c3e9f12b4d'
down_revision: str | None = 'f1a2b3c4d5e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'products',
        sa.Column('photo_urls', sa.JSON(), nullable=False, server_default='[]'),
    )
    op.execute(
        "UPDATE products SET photo_urls = json_build_array(photo_url) "
        "WHERE photo_url IS NOT NULL AND photo_url != ''"
    )
    op.alter_column('products', 'photo_urls', server_default=None)
    op.drop_column('products', 'photo_url')


def downgrade() -> None:
    op.add_column('products', sa.Column('photo_url', sa.String(), nullable=True))
    op.execute(
        "UPDATE products SET photo_url = photo_urls->>0 "
        "WHERE json_array_length(photo_urls) > 0"
    )
    op.drop_column('products', 'photo_urls')
