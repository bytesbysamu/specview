"""Session factory: yields an SQLModel Session bound to the engine singleton."""
from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session

from modules.data.db.engine import get_engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
