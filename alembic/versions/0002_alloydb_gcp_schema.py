"""AlloyDB GCP schema: tenants, tenders, agent_runs, certidoes, hitl_queue, watch_configs, watch_events + RLS

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-23
"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

_TABLES = [
    "tenants",
    "tenders",
    "agent_runs",
    "certidoes",
    "hitl_queue",
    "watch_configs",
    "watch_events",
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # tenants — no RLS (system table)
    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("cnpj", sa.String(18), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="starter"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("idx_tenants_slug", "tenants", ["slug"])

    # tenders
    op.create_table(
        "tenders",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pncp_id", sa.String(255), nullable=False),
        sa.Column("gcs_raw_path", sa.Text(), nullable=True),
        sa.Column("gcs_parsed_path", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("structured_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_tenders_tenant", "tenders", ["tenant_id"])
    op.create_index("idx_tenders_pncp", "tenders", ["pncp_id"])
    op.create_index("idx_tenders_status", "tenders", ["tenant_id", "status"])

    # agent_runs
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tender_id", sa.UUID(), sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("tier", sa.String(50), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_brl", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("eval_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_agent_runs_tenant", "agent_runs", ["tenant_id", "created_at"])
    op.create_index("idx_agent_runs_tender", "agent_runs", ["tender_id"])

    # certidoes
    op.create_table(
        "certidoes",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("gcs_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_certidoes_tenant", "certidoes", ["tenant_id", "tipo"])

    # hitl_queue
    op.create_table(
        "hitl_queue",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tender_id", sa.UUID(), sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=True),
        sa.Column("run_id", sa.String(255), nullable=False),
        sa.Column("action_required", sa.String(100), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("decided_by", sa.String(255), nullable=True),
        sa.Column("decided_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_hitl_tenant_status", "hitl_queue", ["tenant_id", "status"])
    op.create_index("idx_hitl_run_id", "hitl_queue", ["run_id"])

    # watch_configs
    op.create_table(
        "watch_configs",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tender_id", sa.UUID(), sa.ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("portal_url", sa.Text(), nullable=False),
        sa.Column("deadline_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_watch_tenant", "watch_configs", ["tenant_id", "active"])

    # watch_events
    op.create_table(
        "watch_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("tenant_id", sa.UUID(), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("watch_config_id", sa.UUID(), sa.ForeignKey("watch_configs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_watch_events_config", "watch_events", ["watch_config_id", "created_at"])
    op.create_index("idx_watch_events_tenant", "watch_events", ["tenant_id", "created_at"])

    # RLS: enable on all tenant-scoped tables
    for table in _TABLES[1:]:  # skip tenants
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.current_tenant_id')::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid)
            """
        )

    # service account bypass (Cloud Run SA)
    for table in _TABLES[1:]:
        op.execute(
            f"""
            CREATE POLICY sa_bypass ON {table}
            TO licitacerta_sa
            USING (true)
            WITH CHECK (true)
            """
        )


def downgrade() -> None:
    for table in reversed(_TABLES[1:]):
        op.execute(f"DROP POLICY IF EXISTS sa_bypass ON {table}")
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

    for table in reversed(_TABLES):
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
