"""create channels and channel memberships

Revision ID: 0002_channels_memberships
Revises: 0001_initial_users
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0002_channels_memberships"
down_revision = "0001_initial_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("channel_type", sa.String(length=16), server_default="text", nullable=False),
        sa.Column("is_private", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("channel_type = 'text'", name="ck_channels_type"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_channels_owner_id", "channels", ["owner_id"])
    op.create_table(
        "channel_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="member", nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role IN ('owner', 'admin', 'member')", name="ck_channel_membership_role"),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel_id", "user_id", name="uq_channel_membership_channel_user"),
    )
    op.create_index("ix_channel_memberships_channel_id", "channel_memberships", ["channel_id"])
    op.create_index("ix_channel_memberships_user_id", "channel_memberships", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_channel_memberships_user_id", table_name="channel_memberships")
    op.drop_index("ix_channel_memberships_channel_id", table_name="channel_memberships")
    op.drop_table("channel_memberships")
    op.drop_index("ix_channels_owner_id", table_name="channels")
    op.drop_table("channels")
