"""
brokerage_repository.py

Repository for Brokerage entities.

Repositories encapsulate all database access for Brokerage entities.

Business logic does not belong in repositories.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy import select

from src.models.brokerage import Brokerage
from src.repositories.repository_base import RepositoryBase


class BrokerageRepository(RepositoryBase[Brokerage]):
    """
    Repository for Brokerage entities.
    """

    def find_by_id(
        self,
        brokerage_id: int,
    ) -> Brokerage | None:
        """
        Find a brokerage by its primary key.
        """

        statement = (
            select(Brokerage)
            .where(Brokerage.id == brokerage_id)
        )

        return self._scalar(statement)

    def find_by_name(
        self,
        name: str,
    ) -> Brokerage | None:
        """
        Find a brokerage by name.
        """

        statement = (
            select(Brokerage)
            .where(Brokerage.name == name)
        )

        return self._scalar(statement)

    def find_all(self) -> list[Brokerage]:
        """
        Return all brokerages ordered by name.
        """

        statement = (
            select(Brokerage)
            .order_by(Brokerage.name)
        )

        return self._list(statement)

    def exists(
        self,
        name: str,
    ) -> bool:
        """
        Determine whether a brokerage exists.
        """

        return self.find_by_name(name) is not None

    def count(self) -> int:
        """
        Return the number of brokerages.

        Uses SQL COUNT(*) rather than loading every row.
        """

        statement = select(func.count(Brokerage.id))

        result = self.session.scalar(statement)

        return 0 if result is None else int(result)

    def create_if_missing(
        self,
        *,
        name: str,
        importer: str,
        website: str = "",
    ) -> Brokerage:
        """
        Return an existing brokerage or create a new one.

        The brokerage is added to the current session but is not
        committed. The caller is responsible for committing the
        transaction.
        """

        brokerage = self.find_by_name(name)

        if brokerage is not None:
            return brokerage

        brokerage = Brokerage(
            name=name,
            importer=importer,
            website=website,
            active=True,
        )

        self.add(brokerage)

        return brokerage