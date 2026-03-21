"""Initial tables: decisions, ai_analysis_cache, portfolio_briefing_cache

Revision ID: 0001
Revises:
Create Date: 2026-03-21
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("account_id", sa.String(), nullable=False, index=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("decided_by", sa.String(), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_decisions_account_id", "decisions", ["account_id"])

    op.create_table(
        "ai_analysis_cache",
        sa.Column("account_id", sa.String(), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "portfolio_briefing_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("briefing", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("portfolio_briefing_cache")
    op.drop_table("ai_analysis_cache")
    op.drop_index("ix_decisions_account_id", table_name="decisions")
    op.drop_table("decisions")
