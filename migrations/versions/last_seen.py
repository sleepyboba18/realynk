"""add user last seen timestamp

Revision ID: 0005_last_seen
Revises: 0004_messages
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_last_seen"
down_revision = "0004_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "last_seen_at")
