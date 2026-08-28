"""create messages

Revision ID: 0004_messages
Revises: 0003_conversations
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_messages"
down_revision = "0003_conversations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_edited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(channel_id IS NOT NULL AND conversation_id IS NULL) OR "
            "(channel_id IS NULL AND conversation_id IS NOT NULL)",
            name="ck_messages_exactly_one_context",
        ),
        sa.CheckConstraint("length(btrim(content)) > 0", name="ck_messages_content_not_empty"),
        sa.CheckConstraint("length(content) <= 4000", name="ck_messages_content_length"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["channel_id"], ["channels.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_sender_id", "messages", ["sender_id"])
    op.create_index("ix_messages_channel_created_id", "messages", ["channel_id", "created_at", "id"])
    op.create_index("ix_messages_conversation_created_id", "messages", ["conversation_id", "created_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_created_id", table_name="messages")
    op.drop_index("ix_messages_channel_created_id", table_name="messages")
    op.drop_index("ix_messages_sender_id", table_name="messages")
    op.drop_table("messages")
