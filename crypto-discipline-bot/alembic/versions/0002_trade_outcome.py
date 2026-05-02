"""trade outcome fields: outcome, pnl_percent, exit_price, closed_at, notes

Revision ID: 0002_trade_outcome
Revises: 0001_initial
Create Date: 2026-04-30

"""
from alembic import op
import sqlalchemy as sa


revision = "0002_trade_outcome"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trades",
        sa.Column("outcome", sa.String(length=16), nullable=False, server_default="NONE"),
    )
    op.add_column("trades", sa.Column("pnl_percent", sa.Float(), nullable=True))
    op.add_column("trades", sa.Column("exit_price", sa.Float(), nullable=True))
    op.add_column(
        "trades", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("trades", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("trades", "notes")
    op.drop_column("trades", "closed_at")
    op.drop_column("trades", "exit_price")
    op.drop_column("trades", "pnl_percent")
    op.drop_column("trades", "outcome")
