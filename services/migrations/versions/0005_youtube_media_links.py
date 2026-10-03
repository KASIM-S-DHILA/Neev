"""Append-only associations between saved YouTube sources and permitted local media."""
from alembic import op
import sqlalchemy as sa

revision = "0005_youtube_media_links"
down_revision = "0004_visual_content"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("youtube_media_links",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("youtube_source_id", sa.String(36), sa.ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("caption_version_id", sa.String(36), sa.ForeignKey("source_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("media_version_id", sa.String(36), sa.ForeignKey("source_versions.id", ondelete="RESTRICT")),
        sa.Column("youtube_start_seconds", sa.Float, nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.CheckConstraint("youtube_start_seconds >= 0 AND youtube_start_seconds <= 14400", name="youtube_media_offset"))
    op.create_index("ix_youtube_media_source", "youtube_media_links", ["youtube_source_id", "id"])


def downgrade():
    raise RuntimeError("Restore a backup rather than discard saved YouTube media associations.")
