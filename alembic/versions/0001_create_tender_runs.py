"""create tender_runs table

Revision ID: 0001
Revises:
Create Date: 2026-05-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tender_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("edital_id", sa.String(255), nullable=False),
        sa.Column("current_step", sa.String(100), nullable=False),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_tender_runs_edital", "tender_runs", ["edital_id"])
    op.create_index("idx_tender_runs_step", "tender_runs", ["current_step"])


def downgrade() -> None:
    op.drop_index("idx_tender_runs_step", table_name="tender_runs")
    op.drop_index("idx_tender_runs_edital", table_name="tender_runs")
    op.drop_table("tender_runs")
