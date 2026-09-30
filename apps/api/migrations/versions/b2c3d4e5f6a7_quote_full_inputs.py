"""store quote's original pricing inputs (not just the computed result) so

editing a saved piece can reuse the exact same form as creating one

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-30 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("quotes") as batch_op:
        batch_op.add_column(sa.Column("machine_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("material_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("cost_per_kg", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("extra_items", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("print_time_hours", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("depreciation_mode", sa.String(10), nullable=True))
        batch_op.add_column(sa.Column("depreciation_value", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("labor_hours", sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column("profit_margin_percentage", sa.Numeric(6, 3), nullable=True))
        batch_op.create_foreign_key(
            "fk_quotes_machine_id", "machines", ["machine_id"], ["id"]
        )
        batch_op.create_foreign_key(
            "fk_quotes_material_id", "materials", ["material_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("quotes") as batch_op:
        batch_op.drop_constraint("fk_quotes_material_id", type_="foreignkey")
        batch_op.drop_constraint("fk_quotes_machine_id", type_="foreignkey")
        batch_op.drop_column("profit_margin_percentage")
        batch_op.drop_column("labor_hours")
        batch_op.drop_column("depreciation_value")
        batch_op.drop_column("depreciation_mode")
        batch_op.drop_column("print_time_hours")
        batch_op.drop_column("extra_items")
        batch_op.drop_column("cost_per_kg")
        batch_op.drop_column("material_id")
        batch_op.drop_column("machine_id")
