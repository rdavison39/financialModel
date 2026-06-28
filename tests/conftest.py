"""
conftest.py

Shared pytest fixtures.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from src.database.base import Base


@pytest.fixture
def session() -> Session:
    """
    Create a fresh in-memory SQLite database for each test.

    Every test receives a completely clean database.
    """

    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
    )

    Base.metadata.create_all(engine)

    SessionFactory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    db = SessionFactory()

    try:
        yield db
    finally:
        db.close()
        engine.dispose()