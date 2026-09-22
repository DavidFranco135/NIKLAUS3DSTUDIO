"""customers and project quote customer fk

Revision ID: 9999a7d7f2af
Revises: 9a6d1ea40673
Create Date: 2026-09-21 22:45:00.363756
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '9999a7d7f2af'
down_revision: str | None = '9a6d1ea40673'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('customers',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('phone', sa.String(), nullable=True),
    sa.Column('document', sa.String(), nullable=True),
    sa.Column('address', sa.JSON(), nullable=True),
    sa.Column('notes', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_customers_organization_id'), 'customers', ['organization_id'], unique=False)

    op.add_column('projects', sa.Column('customer_id', sa.Uuid(), nullable=True))
    with op.batch_alter_table('projects') as batch_op:
        batch_op.create_index(op.f('ix_projects_customer_id'), ['customer_id'], unique=False)
        batch_op.create_foreign_key('fk_projects_customer_id', 'customers', ['customer_id'], ['id'])

    with op.batch_alter_table('quotes') as batch_op:
        batch_op.create_foreign_key('fk_quotes_customer_id', 'customers', ['customer_id'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('quotes') as batch_op:
        batch_op.drop_constraint('fk_quotes_customer_id', type_='foreignkey')

    with op.batch_alter_table('projects') as batch_op:
        batch_op.drop_constraint('fk_projects_customer_id', type_='foreignkey')
        batch_op.drop_index(op.f('ix_projects_customer_id'))
    op.drop_column('projects', 'customer_id')

    op.drop_index(op.f('ix_customers_organization_id'), table_name='customers')
    op.drop_table('customers')
