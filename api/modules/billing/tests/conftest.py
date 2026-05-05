"""In-memory SQLite isolation for every billing test.

Patches modules.data.db.session.get_session so service.py and routes.py
both transparently use the per-test in-memory engine. Tests never touch
the real spec_doc.db file.
"""
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, SQLModel

# Importing these modules registers their tables on SQLModel.metadata.
from modules.auth.models import User  # noqa: F401
from modules.billing.models import Subscription  # noqa: F401


@pytest.fixture
def billing_engine():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(autouse=True)
def patched_session(monkeypatch, billing_engine):
    @contextmanager
    def _session():
        with Session(billing_engine) as session:
            yield session

    monkeypatch.setattr("modules.data.db.session.get_session", _session)
    monkeypatch.setattr("modules.billing.service.get_session", _session)
    monkeypatch.setattr("modules.billing.routes.get_session", _session)
    yield


@pytest.fixture
def db_session(billing_engine):
    """Open a session against the in-memory engine for arrange/assert helpers."""
    with Session(billing_engine) as session:
        yield session


@pytest.fixture
def make_user(db_session):
    """Insert a User row and return it."""

    def _make(auth_user_id: str = "auth-1", email: str = "u1@example.com"):
        user = User(auth_user_id=auth_user_id, email=email)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make
