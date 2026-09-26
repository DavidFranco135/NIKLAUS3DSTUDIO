"""quote piece fields

Revision ID: c97e1a4d8996
Revises: fb506c6bfdca
Create Date: 2026-09-26 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'c97e1a4d8996'
down_revision: str | None = 'fb506c6bfdca'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('quotes') as batch_op:
        batch_op.add_column(sa.Column('piece_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('printer_name', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('weight_g', sa.Numeric(precision=10, scale=2, asdecimal=False), nullable=True))
        batch_op.add_column(sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    with op.batch_alter_table('quotes') as batch_op:
        batch_op.drop_column('quantity')
        batch_op.drop_column('weight_g')
        batch_op.drop_column('printer_name')
        batch_op.drop_column('piece_name')
