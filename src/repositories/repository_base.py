"""
repository_base.py

Defines the abstract base repository used by all repositories in the
Davison Financial Model.

The RepositoryBase class provides common persistence operations shared
by all repositories.

Business logic does not belong in repositories.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from typing import Generic
from typing import TypeVar

from sqlalchemy import Select
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType")


class RepositoryBase(Generic[ModelType]):
    """
    Base class for all repositories.
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize the repository.

        Args:
            session:
                SQLAlchemy session.
        """

        self._session = session

    @property
    def session(self) -> Session:
        """
        Return the SQLAlchemy session.
        """

        return self._session

    #
    # Protected Query Helpers
    #

    def _scalar(
        self,
        statement: Select,
    ) -> ModelType | None:
        """
        Execute a query expected to return zero or one row.
        """

        return self.session.scalar(statement)

    def _list(
        self,
        statement: Select,
    ) -> list[ModelType]:
        """
        Execute a query returning multiple rows.
        """

        return list(self.session.scalars(statement))

    #
    # Persistence Operations
    #

    def add(
        self,
        entity: ModelType,
    ) -> None:
        """
        Add an entity to the current session.
        """

        self.session.add(entity)

    def add_all(
        self,
        entities: list[ModelType],
    ) -> None:
        """
        Add multiple entities to the current session.
        """

        self.session.add_all(entities)

    def delete(
        self,
        entity: ModelType,
    ) -> None:
        """
        Delete an entity.
        """

        self.session.delete(entity)

    def flush(self) -> None:
        """
        Flush pending changes.
        """

        self.session.flush()

    def refresh(
        self,
        entity: ModelType,
    ) -> None:
        """
        Refresh an entity from the database.
        """

        self.session.refresh(entity)

    #
    # Transaction Control
    #

    def commit(self) -> None:
        """
        Commit the current transaction.
        """

        self.session.commit()

    def rollback(self) -> None:
        """
        Roll back the current transaction.
        """

        self.session.rollback()