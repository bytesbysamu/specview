"""Database engine factory.

Resolves DATABASE_URL at runtime (SQLite for dev, Postgres for prod).
Provides a module-level singleton engine via get_engine().
"""
import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def _build_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    spec_doc_dir = os.getenv("SPEC_DOC_DIR", "/data")
    db_path = os.path.join(spec_doc_dir, "spec_doc.db")
    return f"sqlite:///{db_path}"


def create_db_engine() -> Engine:
    url = _build_database_url()
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


_engine: Optional[Engine] = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_db_engine()
    return _engine
