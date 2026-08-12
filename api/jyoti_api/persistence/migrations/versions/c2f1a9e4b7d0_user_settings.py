"""add user_settings

Revision ID: c2f1a9e4b7d0
Revises: 00d42b4bc95e
Create Date: 2026-08-08 10:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = 'c2f1a9e4b7d0'
down_revision = '00d42b4bc95e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The app's boot-time create_all may have already made this table on a
    # fresh database; only create it here when it is missing.
    if "user_settings" in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'user_settings',
        sa.Column('user_id', sa.String(length=32), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
    )


def downgrade() -> None:
    op.drop_table('user_settings')
