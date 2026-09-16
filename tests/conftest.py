"""
Pytest fixtures for the financial model test suite.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.models.base import Base


@pytest.fixture
def session() -> Session:
    """Create a fresh in-memory database session for a test."""

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()