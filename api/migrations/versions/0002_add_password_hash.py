"""Add password_hash to user, make auth_user_id nullable.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("password_hash", sa.Text(), nullable=True))
    op.alter_column("user", "auth_user_id", nullable=True)


def downgrade() -> None:
    op.drop_column("user", "password_hash")
    op.alter_column("user", "auth_user_id", nullable=False)
