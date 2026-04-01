"""Rename stripe fields to generic payment fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename columns in orders table
    op.alter_column('orders', 'stripe_payment_intent', new_column_name='payment_reference')
    op.alter_column('orders', 'stripe_charge_id', new_column_name='payment_id')


def downgrade() -> None:
    # Rename columns back to stripe-specific names
    op.alter_column('orders', 'payment_reference', new_column_name='stripe_payment_intent')
    op.alter_column('orders', 'payment_id', new_column_name='stripe_charge_id')
