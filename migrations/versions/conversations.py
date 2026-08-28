"""create conversations and conversation participants

Revision ID: 0003_conversations
Revises: 0002_channels_memberships
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_conversations"
down_revision = "0002_channels_memberships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_type", sa.String(length=16), server_default="direct", nullable=False),
        sa.Column("participant_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("conversation_type = 'direct'", name="ck_conversations_type"),
        sa.CheckConstraint("participant_a_id <> participant_b_id", name="ck_conversations_distinct_pair"),
        sa.ForeignKeyConstraint(["participant_a_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["participant_b_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participant_a_id", "participant_b_id", name="uq_conversations_participant_pair"),
    )
    op.create_index("ix_conversations_participant_a_id", "conversations", ["participant_a_id"])
    op.create_index("ix_conversations_participant_b_id", "conversations", ["participant_b_id"])
    op.create_table(
        "conversation_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("conversation_id", "user_id", name="uq_conversation_participant"),
    )
    op.create_index("ix_conversation_participants_conversation_id", "conversation_participants", ["conversation_id"])
    op.create_index("ix_conversation_participants_user_id", "conversation_participants", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_conversation_participants_user_id", table_name="conversation_participants")
    op.drop_index("ix_conversation_participants_conversation_id", table_name="conversation_participants")
    op.drop_table("conversation_participants")
    op.drop_index("ix_conversations_participant_b_id", table_name="conversations")
    op.drop_index("ix_conversations_participant_a_id", table_name="conversations")
    op.drop_table("conversations")
