"""Durable jobs; existing workspace and original file records are preserved."""
from alembic import op
import sqlalchemy as sa

revision = "0002_background_jobs"
down_revision = "0001_local_storage"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(200), sa.ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subject_id", sa.String(200)),
        sa.Column("source_version_id", sa.String(36), sa.ForeignKey("source_versions.id", ondelete="RESTRICT")),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("stage", sa.String(80), nullable=False),
        sa.Column("done", sa.Integer, nullable=False),
        sa.Column("total", sa.Integer, nullable=False),
        sa.Column("checkpoint_json", sa.Text, nullable=False),
        sa.Column("payload_json", sa.Text, nullable=False),
        sa.Column("result_json", sa.Text),
        sa.Column("error", sa.String(1000)),
        sa.Column("cancel_requested", sa.Boolean, nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False),
        sa.Column("failures", sa.Integer, nullable=False),
        sa.Column("max_attempts", sa.Integer, nullable=False),
        sa.Column("recoveries", sa.Integer, nullable=False),
        sa.Column("owner", sa.String(36)),
        sa.Column("available_at", sa.Float, nullable=False),
        sa.Column("created_at", sa.Float, nullable=False),
        sa.Column("updated_at", sa.Float, nullable=False),
        sa.ForeignKeyConstraint(["workspace_id", "subject_id"], ["subjects.workspace_id", "subjects.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("kind", "source_version_id"),
        sa.CheckConstraint("state IN ('queued', 'running', 'succeeded', 'partial', 'failed', 'cancelled')", name="job_state"))
    op.create_index("ix_jobs_queue", "jobs", ["state", "available_at", "created_at"])
    op.create_index("ix_jobs_workspace", "jobs", ["workspace_id", "created_at"])


def downgrade():
    raise RuntimeError("Restore an explicit backup instead of deleting job history.")
