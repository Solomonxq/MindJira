"""create enrichments table

Revision ID: 0001_create_enrichments_table
Revises:
Create Date: 2026-06-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_create_enrichments_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "enrichments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("issue_key", sa.String(length=50), nullable=False, index=True),
        sa.Column("issue_type", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default=sa.text("'uk'")),
        sa.Column("original_description", sa.Text(), nullable=True),
        sa.Column("generated_description", sa.Text(), nullable=False),
        sa.Column("applied_to_jira", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("enrichments")
