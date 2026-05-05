"""Alembic env hook.

Imports SQLModel metadata for all currently-defined entities, resolves
DATABASE_URL at runtime, and drives both offline and online migration modes.
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure api/ is importable when alembic is invoked from api/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all table-bearing models so SQLModel registers their metadata.
# Subscription and UsageCounter models will be added by the monetisation epic;
# the 0001 migration creates their tables ahead of those model classes
# (Locked decision: schema lands atomically; classes ship in Mon-T2/T3).
from modules.auth.models import User  # noqa: F401, E402
from modules.data.projects.models import Project  # noqa: F401, E402
from sqlmodel import SQLModel  # noqa: E402

config = context.config

# Resolve DATABASE_URL — always overrides the blank sqlalchemy.url in alembic.ini.
_spec_doc_dir = os.getenv("SPEC_DOC_DIR", "/data")
_fallback = f"sqlite:///{os.path.join(_spec_doc_dir, 'spec_doc.db')}"
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", _fallback))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
