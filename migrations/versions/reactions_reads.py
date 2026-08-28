"""create message reactions and reads

Revision ID: 0006_reactions_reads
Revises: 0005_last_seen
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_reactions_reads"
down_revision = "0005_last_seen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "message_reactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("emoji", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "user_id", "emoji", name="uq_message_reaction_user_emoji"),
    )
    op.create_index("ix_message_reactions_message_id", "message_reactions", ["message_id"])
    op.create_index("ix_message_reactions_user_id", "message_reactions", ["user_id"])
    op.create_table(
        "message_reads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "user_id", name="uq_message_read_user"),
    )
    op.create_index("ix_message_reads_message_id", "message_reads", ["message_id"])
    op.create_index("ix_message_reads_user_id", "message_reads", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_message_reads_user_id", table_name="message_reads")
    op.drop_index("ix_message_reads_message_id", table_name="message_reads")
    op.drop_table("message_reads")
    op.drop_index("ix_message_reactions_user_id", table_name="message_reactions")
    op.drop_index("ix_message_reactions_message_id", table_name="message_reactions")
    op.drop_table("message_reactions")
