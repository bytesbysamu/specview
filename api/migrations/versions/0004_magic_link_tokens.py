"""magic_link_tokens table for passwordless auth.

Revision ID: 0004
Revises: 0003

Stores the SHA-256 hash of each single-use magic-link token (never the raw
token), the requesting email, an optional FK to an existing user, a 15-minute
expiry, and a used flag. The legacy user.password_hash column is intentionally
left in place (magic-link only; dropping it is a live-data risk).
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "magic_link_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_magic_link_tokens_token_hash"),
    )
    op.create_index(
        "ix_magic_link_tokens_token_hash", "magic_link_tokens", ["token_hash"]
    )
    op.create_index("ix_magic_link_tokens_email", "magic_link_tokens", ["email"])


def downgrade() -> None:
    op.drop_index("ix_magic_link_tokens_email", table_name="magic_link_tokens")
    op.drop_index("ix_magic_link_tokens_token_hash", table_name="magic_link_tokens")
    op.drop_table("magic_link_tokens")
