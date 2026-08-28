"""create attachments

Revision ID: 0008_attachments
Revises: 0007_notifications
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008_attachments"
down_revision = "0007_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploader_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("extension", sa.String(length=16), nullable=False),
        sa.Column("attachment_type", sa.String(length=16), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attachment_type IN ('image', 'document', 'video', 'audio', 'file')", name="ck_attachments_type"),
        sa.CheckConstraint("file_size > 0", name="ck_attachments_file_size"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uploader_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index("ix_attachments_message_active", "attachments", ["message_id", "deleted_at", "created_at"])
    op.create_index("ix_attachments_uploader_created", "attachments", ["uploader_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_attachments_uploader_created", table_name="attachments")
    op.drop_index("ix_attachments_message_active", table_name="attachments")
    op.drop_table("attachments")
