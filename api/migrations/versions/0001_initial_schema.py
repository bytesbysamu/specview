"""initial schema: user, project, subscription, usage_counter

Revision ID: 0001
Revises:
Create Date: 2026-04-26

Covers all four foundational SaaS tables atomically:
  - user            (Pers-T1, this task)
  - project         (Pers-T1, this task)
  - subscription    (Mon-T2 — column shape locked here, model class ships there)
  - usage_counter   (Mon-T3 — column shape locked here, model class ships there)

Per the locked-decision contract for SaaS Persistence Task 1, the migration
ships all four tables together so Postgres never enters a state where a
foreign-key references a missing table. The Subscription and UsageCounter
SQLModel classes are added by the monetisation epic (Mon-T2 / Mon-T3); only
their DDL lives here.
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("auth_user_id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_user_email"),
        sa.UniqueConstraint("auth_user_id", name="uq_user_auth_user_id"),
    )
    op.create_index("ix_user_auth_user_id", "user", ["auth_user_id"])

    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("git_repo_path", sa.String(), nullable=False),
        sa.Column("latest_commit_sha", sa.String(), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_project_slug"),
    )
    op.create_index("ix_project_slug", "project", ["slug"])

    # --- Monetisation epic tables (Mon-T2 / Mon-T3 own the model classes) ---
    op.create_table(
        "subscription",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("current_period_start", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_subscription_user_id"),
    )
    op.create_index("ix_subscription_user_id", "subscription", ["user_id"])

    op.create_table(
        "usage_counter",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("feature", sa.String(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "feature", "date",
            name="uq_usage_counter_user_feature_date",
        ),
    )
    op.create_index("ix_usage_counter_user_id", "usage_counter", ["user_id"])
    op.create_index("ix_usage_counter_feature", "usage_counter", ["feature"])
    op.create_index("ix_usage_counter_date", "usage_counter", ["date"])


def downgrade() -> None:
    op.drop_index("ix_usage_counter_date", table_name="usage_counter")
    op.drop_index("ix_usage_counter_feature", table_name="usage_counter")
    op.drop_index("ix_usage_counter_user_id", table_name="usage_counter")
    op.drop_table("usage_counter")

    op.drop_index("ix_subscription_user_id", table_name="subscription")
    op.drop_table("subscription")

    op.drop_index("ix_project_slug", table_name="project")
    op.drop_table("project")

    op.drop_index("ix_user_auth_user_id", table_name="user")
    op.drop_table("user")
