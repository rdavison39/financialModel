"""
database.py

Provides the SQLite database connection, SQLAlchemy engine,
and session management for the Financial Model application.

Author: Ron Davison / ChatGPT
"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from database.base import Base


class Database:
    """
    Handles creation of the SQLite database and SQLAlchemy sessions.
    """

    def __init__(self, database_file: Path):
        """
        Initialize the database.

        Args:
            database_file:
                Full path to the SQLite database file.
        """

        self.database_file = database_file

        database_url = f"sqlite:///{database_file}"

        self.engine = create_engine(
            database_url,
            echo=False,
            future=True,
        )

        self.Session = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )

    def create_database(self) -> None:
        """
        Create all database tables.

        Safe to call multiple times.
        """

        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """
        Return a SQLAlchemy session.

        Returns:
            SQLAlchemy Session object.
        """

        return self.Session()

    def close(self) -> None:
        """
        Dispose of the database engine.
        """

        self.engine.dispose()