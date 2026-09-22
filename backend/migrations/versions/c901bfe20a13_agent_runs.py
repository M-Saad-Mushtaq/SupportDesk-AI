"""Persistent agent runs and handling revision guards."""
from alembic import op
import sqlalchemy as sa

revision = "c901bfe20a13"
down_revision = "b7139a42c801"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("conversations", sa.Column("handling_revision", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("messages", sa.Column("origin", sa.String(), nullable=False, server_default="sample"))
    op.create_table("agent_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("conversation_id", sa.String(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("customer_message_id", sa.String(), sa.ForeignKey("messages.id"), nullable=False, unique=True),
        sa.Column("response_message_id", sa.String(), sa.ForeignKey("messages.id"), nullable=True, unique=True),
        sa.Column("provider", sa.String(), nullable=False), sa.Column("model", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False), sa.Column("handling_revision", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("started_at", sa.String(), nullable=True), sa.Column("finished_at", sa.String(), nullable=True),
        sa.Column("retry_at", sa.String(), nullable=True), sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True), sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("request_count", sa.Integer(), nullable=False), sa.Column("tool_count", sa.Integer(), nullable=False),
        sa.Column("usage", sa.JSON(), nullable=False), sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.JSON(), nullable=False),
        sa.CheckConstraint("status IN ('pending','running','completed','failed','cancelled','interrupted')", name="valid_run_status"))
    op.create_index("ix_agent_runs_conversation_id", "agent_runs", ["conversation_id"])
    op.create_index("one_active_agent_run", "agent_runs", ["conversation_id"], unique=True, sqlite_where=sa.text("status IN ('pending','running')"))
    op.create_table("agent_tools",
        sa.Column("id", sa.String(), primary_key=True), sa.Column("run_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False), sa.Column("name", sa.String(), nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False), sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False), sa.Column("attempt", sa.Integer(), nullable=False),
        sa.UniqueConstraint("run_id", "fingerprint"))
    op.create_index("ix_agent_tools_run_id", "agent_tools", ["run_id"])


def downgrade():
    op.drop_table("agent_tools")
    op.drop_table("agent_runs")
    with op.batch_alter_table("messages") as batch:
        batch.drop_column("origin")
    with op.batch_alter_table("conversations") as batch:
        batch.drop_column("handling_revision")
