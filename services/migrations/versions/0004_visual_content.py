"""Preserve visual provenance without changing existing source units."""
from alembic import op
import sqlalchemy as sa

revision = "0004_visual_content"
down_revision = "0003_content_units"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("content_units", sa.Column("metadata_json", sa.Text, nullable=False, server_default="{}"))


def downgrade():
    raise RuntimeError("Restore a backup rather than discard visual provenance.")
