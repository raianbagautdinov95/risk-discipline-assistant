"""daily plans — morning check-in answers

Revision ID: 0003_daily_plan
Revises: 0002_trade_outcome
Create Date: 2026-04-30
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_daily_plan"
down_revision = "0002_trade_outcome"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("intent", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "plan_date", name="uq_user_plandate"),
    )


def downgrade() -> None:
    op.drop_table("daily_plans")
