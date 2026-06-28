"""
import_repository.py

Repository for Import entities.

Repositories encapsulate all database access for Import entities.

Business logic does not belong in repositories.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import select

from src.models.import_record import Import
from src.repositories.repository_base import RepositoryBase


class ImportRepository(RepositoryBase[Import]):
    """
    Repository for Import entities.
    """

    def find_by_id(
        self,
        import_id: int,
    ) -> Import | None:
        """
        Find an import by its primary key.
        """

        statement = (
            select(Import)
            .where(Import.id == import_id)
        )

        return self._scalar(statement)

    def find_latest(self) -> Import | None:
        """
        Return the most recent import.
        """

        statement = (
            select(Import)
            .order_by(desc(Import.import_timestamp))
            .limit(1)
        )

        return self._scalar(statement)

    def find_by_brokerage(
        self,
        brokerage_id: int,
    ) -> list[Import]:
        """
        Return all imports for a brokerage ordered newest first.
        """

        statement = (
            select(Import)
            .where(Import.brokerage_id == brokerage_id)
            .order_by(desc(Import.import_timestamp))
        )

        return self._list(statement)

    def latest_for_brokerage(
        self,
        brokerage_id: int,
    ) -> Import | None:
        """
        Return the most recent import for a brokerage.
        """

        statement = (
            select(Import)
            .where(Import.brokerage_id == brokerage_id)
            .order_by(desc(Import.import_timestamp))
            .limit(1)
        )

        return self._scalar(statement)

    def find_all(self) -> list[Import]:
        """
        Return all imports ordered newest first.
        """

        statement = (
            select(Import)
            .order_by(desc(Import.import_timestamp))
        )

        return self._list(statement)

    def count(self) -> int:
        """
        Return the number of imports.

        Uses SQL COUNT(*) rather than loading every row.
        """

        statement = select(func.count(Import.id))

        result = self.session.scalar(statement)

        return 0 if result is None else int(result)