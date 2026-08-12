"""add feedback

Revision ID: a7b9c1d3e5f7
Revises: c2f1a9e4b7d0
Create Date: 2026-08-08 11:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = 'a7b9c1d3e5f7'
down_revision = 'c2f1a9e4b7d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The app's boot-time create_all may have already made this table on a
    # fresh database; only create it here when it is missing.
    if "feedback" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'feedback',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('meta', sa.JSON(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_feedback_user_id', 'feedback', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_feedback_user_id', table_name='feedback')
    op.drop_table('feedback')
