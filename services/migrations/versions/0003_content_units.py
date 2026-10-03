"""Version-bound content units with exact physical page or decoded-text locators."""
from alembic import op
import sqlalchemy as sa

revision = "0003_content_units"
down_revision = "0002_background_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("content_units",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_version_id", sa.String(36), sa.ForeignKey("source_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ordinal", sa.Integer, nullable=False),
        sa.Column("locator_json", sa.Text, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("warning", sa.String(1000)),
        sa.Column("engine", sa.String(80), nullable=False),
        sa.UniqueConstraint("source_version_id", "ordinal"),
        sa.CheckConstraint("status IN ('text', 'needs_ocr', 'empty', 'unreadable', 'too_large', 'suspect')", name="content_status"))
    op.create_index("ix_content_version", "content_units", ["source_version_id", "ordinal"])


def downgrade():
    raise RuntimeError("Restore an explicit backup instead of deleting extracted source locations.")
