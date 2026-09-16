"""
Database configuration and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

DATABASE_URL = "sqlite:///financial_model.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
)


def get_session() -> Session:
    """Create and return a new database session."""
    return Session(engine)