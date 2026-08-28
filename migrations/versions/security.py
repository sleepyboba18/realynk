"""add security rate limiting and event tracking

Revision ID: 0009_security
Revises: 0008_attachments
Create Date: 2026-08-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_security"
down_revision = "0008_attachments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_buckets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rate_limit_buckets_key", "rate_limit_buckets", ["key"])
    op.create_index("ix_rate_limit_buckets_scope", "rate_limit_buckets", ["scope"])
    op.create_index("ix_rate_limit_buckets_expires_at", "rate_limit_buckets", ["expires_at"])
    op.create_index("ix_rate_limit_buckets_key_scope_window", "rate_limit_buckets", ["key", "scope", "window_start"])

    op.create_table(
        "security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("route", sa.String(length=255), nullable=True),
        sa.Column("event_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_user_id", "security_events", ["user_id"])
    op.create_index("ix_security_events_ip_address", "security_events", ["ip_address"])
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])
    op.create_index("ix_security_event_type_user_ip_created", "security_events", ["event_type", "user_id", "ip_address", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_security_event_type_user_ip_created", table_name="security_events")
    op.drop_index("ix_security_events_created_at", table_name="security_events")
    op.drop_index("ix_security_events_ip_address", table_name="security_events")
    op.drop_index("ix_security_events_user_id", table_name="security_events")
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_table("security_events")
    op.drop_index("ix_rate_limit_buckets_key_scope_window", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_expires_at", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_scope", table_name="rate_limit_buckets")
    op.drop_index("ix_rate_limit_buckets_key", table_name="rate_limit_buckets")
    op.drop_table("rate_limit_buckets")
