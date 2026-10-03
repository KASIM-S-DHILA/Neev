"""Initial local workspace and immutable source version storage."""
from alembic import op
import sqlalchemy as sa

revision = "0001_local_storage"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("workspaces",
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("name_key", sa.String(120), nullable=False, unique=True),
        sa.Column("revision", sa.Integer, nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False))
    op.create_table("subjects",
        sa.Column("workspace_id", sa.String(200), sa.ForeignKey("workspaces.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("name_key", sa.String(120), nullable=False),
        sa.Column("icon", sa.String(20), nullable=False),
        sa.Column("demo", sa.Boolean, nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.UniqueConstraint("workspace_id", "name_key"))
    op.create_table("topics",
        sa.Column("workspace_id", sa.String(200), primary_key=True),
        sa.Column("subject_id", sa.String(200), primary_key=True),
        sa.Column("id", sa.String(200), primary_key=True),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("title_key", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("unit", sa.String(80), nullable=False),
        sa.Column("read", sa.Boolean, nullable=False),
        sa.Column("read_minutes", sa.Integer),
        sa.Column("lesson", sa.String(30)),
        sa.Column("position", sa.Integer, nullable=False),
        sa.ForeignKeyConstraint(["workspace_id", "subject_id"], ["subjects.workspace_id", "subjects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workspace_id", "subject_id", "title_key"))
    op.create_table("workspace_sessions",
        sa.Column("workspace_id", sa.String(200), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("layout_json", sa.Text, nullable=False))
    op.create_table("sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(200), nullable=False),
        sa.Column("subject_id", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("name_key", sa.String(510), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("next_version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id", "subject_id"], ["subjects.workspace_id", "subjects.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("workspace_id", "subject_id", "name_key"))
    op.create_table("source_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("relative_path", sa.String(100), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.UniqueConstraint("source_id", "version"),
        sa.UniqueConstraint("source_id", "sha256"))
    op.create_index("ix_source_versions_source_id", "source_versions", ["source_id"])


def downgrade():
    raise RuntimeError("Destructive storage downgrades are not supported. Restore an explicit backup instead.")
