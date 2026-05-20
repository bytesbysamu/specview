"""Make project.user_id nullable and add anonymous boolean column.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("project", "user_id", nullable=True)
    op.add_column(
        "project",
        sa.Column(
            "anonymous",
            sa.Boolean(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("project", "anonymous")
    op.alter_column("project", "user_id", nullable=False)
