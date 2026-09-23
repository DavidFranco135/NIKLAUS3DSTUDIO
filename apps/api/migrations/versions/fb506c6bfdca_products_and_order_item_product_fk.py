"""products and order item product fk

Revision ID: fb506c6bfdca
Revises: a64f7589aaf0
Create Date: 2026-09-22 23:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'fb506c6bfdca'
down_revision: str | None = 'a64f7589aaf0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('products',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('print_time_hours', sa.Numeric(precision=10, scale=2, asdecimal=False), nullable=True),
    sa.Column('machine_id', sa.Uuid(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.ForeignKeyConstraint(['machine_id'], ['machines.id'], ),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_organization_id'), 'products', ['organization_id'], unique=False)

    op.create_table('product_materials',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('product_id', sa.Uuid(), nullable=False),
    sa.Column('material_id', sa.Uuid(), nullable=False),
    sa.Column('quantity_g', sa.Numeric(precision=12, scale=3, asdecimal=False), nullable=False),
    sa.ForeignKeyConstraint(['material_id'], ['materials.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_materials_product_id'), 'product_materials', ['product_id'], unique=False)
    op.create_index(op.f('ix_product_materials_material_id'), 'product_materials', ['material_id'], unique=False)

    with op.batch_alter_table('order_items') as batch_op:
        batch_op.add_column(sa.Column('product_id', sa.Uuid(), nullable=True))
        batch_op.create_index(op.f('ix_order_items_product_id'), ['product_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_order_items_product_id', 'products', ['product_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('order_items') as batch_op:
        batch_op.drop_constraint('fk_order_items_product_id', type_='foreignkey')
        batch_op.drop_index(op.f('ix_order_items_product_id'))
        batch_op.drop_column('product_id')

    op.drop_index(op.f('ix_product_materials_material_id'), table_name='product_materials')
    op.drop_index(op.f('ix_product_materials_product_id'), table_name='product_materials')
    op.drop_table('product_materials')

    op.drop_index(op.f('ix_products_organization_id'), table_name='products')
    op.drop_table('products')
