"""product stock_quantity

Revision ID: 2e31188d821f
Revises: a7c3e9f12b4d
Create Date: 2026-10-02 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2e31188d821f"
down_revision: str | None = "a7c3e9f12b4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("products", sa.Column("stock_quantity", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("products", "stock_quantity")
