"""soft delete columns for materials, products, inventory items, cost
profiles, quotes, financial transactions and machines

Revision ID: 56e04fb55548
Revises: c97e1a4d8996
Create Date: 2026-09-29 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '56e04fb55548'
down_revision: str | None = 'c97e1a4d8996'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = [
    "materials",
    "products",
    "inventory_items",
    "cost_profiles",
    "quotes",
    "financial_transactions",
    "machines",
]


def upgrade() -> None:
    for table in TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for table in reversed(TABLES):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("deleted_at")
