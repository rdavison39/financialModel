"""
database.py

Database service for the Davison Financial Model.

Responsibilities
----------------
* Create the SQLite database
* Create all tables
* Manage SQLAlchemy sessions
* Dispose of connections cleanly

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.database.base import Base
from src.utils.logger import logger


class DatabaseService:
    """
    Central database manager.
    """

    def __init__(self) -> None:

        #
        # Ensure database folder exists.
        #

        settings.database_folder.mkdir(
            parents=True,
            exist_ok=True,
        )

        database_url = f"sqlite:///{settings.database_file}"

        self.engine = create_engine(
            database_url,
            echo=False,
            future=True,
        )

        self.session_factory = scoped_session(
            sessionmaker(
                bind=self.engine,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            )
        )

    def create_database(self) -> None:
        """
        Create all database tables.

        Safe to call multiple times.
        """

        logger.info("Creating database...")

        Base.metadata.create_all(self.engine)

        logger.info("Database ready.")

    def get_session(self) -> Session:
        """
        Returns a SQLAlchemy session.
        """

        return self.session_factory()

    def close(self) -> None:
        """
        Close all database connections.
        """

        logger.info("Closing database.")

        self.session_factory.remove()

        self.engine.dispose()


#
# Singleton instance
#

database = DatabaseService()