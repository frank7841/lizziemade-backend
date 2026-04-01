"""Add digital fields and difficulty level to products

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the DifficultyLevel enum type in Postgres
    difficultylevel = postgresql.ENUM(
        'beginner', 'easy', 'intermediate', 'advanced', 'expert',
        name='difficultylevel'
    )
    difficultylevel.create(op.get_bind(), checkfirst=True)

    # Add new columns to products
    op.add_column('products', sa.Column(
        'is_digital', sa.Boolean(), nullable=False, server_default='false'
    ))
    op.add_column('products', sa.Column(
        'difficulty_level',
        sa.Enum('beginner', 'easy', 'intermediate', 'advanced', 'expert', name='difficultylevel'),
        nullable=True
    ))
    op.add_column('products', sa.Column(
        'file_url', sa.String(500), nullable=True
    ))


def downgrade() -> None:
    op.drop_column('products', 'file_url')
    op.drop_column('products', 'difficulty_level')
    op.drop_column('products', 'is_digital')

    # Drop the enum type
    difficultylevel = postgresql.ENUM(name='difficultylevel')
    difficultylevel.drop(op.get_bind(), checkfirst=True)
