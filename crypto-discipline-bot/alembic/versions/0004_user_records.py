"""user_records: personal best cache

Revision ID: 0004_user_records
Revises: 0003_daily_plan
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_user_records"
down_revision = "0003_daily_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("best_win_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "best_discipline_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "best_pnl_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "allowed_milestone", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("win_milestone", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("user_records")
