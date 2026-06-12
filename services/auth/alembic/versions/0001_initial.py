"""initial

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("role", sa.Enum("USER", "ADMIN", name="userrole"), nullable=False, server_default=sa.text("'USER'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email"),
        sa.Index("ix_users_email", "email"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan", sa.Enum("free", "pro", "business", name="subscriptionplan"), nullable=False, server_default=sa.text("'free'")),
        sa.Column("status", sa.Enum("active", "past_due", "canceled", name="subscriptionstatus"), nullable=False, server_default=sa.text("'active'")),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id"),
        sa.Index("ix_subscriptions_user_id", "user_id"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Index("ix_refresh_tokens_user_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_table("subscriptions")
    op.drop_table("users")
    op.execute('DROP TYPE IF EXISTS "userrole"')
    op.execute('DROP TYPE IF EXISTS "subscriptionplan"')
    op.execute('DROP TYPE IF EXISTS "subscriptionstatus"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
