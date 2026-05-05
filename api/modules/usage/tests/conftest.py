"""Test fixtures for the usage module.

`session` yields a fresh SQLite-in-memory Session with the User and
UsageCounter tables created via `SQLModel.metadata.create_all`. Importing
both models inside the fixture guarantees the FK target table exists
before `usage_counter` is created on the same connection.
"""
from __future__ import annotations

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

# Importing both registers them with SQLModel.metadata before create_all.
from modules.auth.models import User  # noqa: F401
from modules.usage.models import UsageCounter  # noqa: F401


@pytest.fixture
def session():
    # StaticPool keeps a single connection for the whole test, so the
    # in-memory database survives across statements and the
    # ON CONFLICT DO UPDATE upsert can see prior writes.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
