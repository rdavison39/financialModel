"""
holding_snapshot_repository.py

Repository for HoldingSnapshot entities.

Repositories encapsulate all database access for HoldingSnapshot
entities.

Business logic does not belong in repositories.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy import select

from src.models.holding_snapshot import HoldingSnapshot
from src.repositories.repository_base import RepositoryBase


class HoldingSnapshotRepository(
    RepositoryBase[HoldingSnapshot]
):
    """
    Repository for HoldingSnapshot entities.
    """

    def find_all(
        self,
    ) -> list[HoldingSnapshot]:
        """
        Return all holding snapshots.
        """

        statement = (
            select(HoldingSnapshot)
            .order_by(
                HoldingSnapshot.account_id,
                HoldingSnapshot.company_id,
                HoldingSnapshot.import_id,
            )
        )

        return self._list(statement)

    def find_by_id(
        self,
        holding_snapshot_id: int,
    ) -> HoldingSnapshot | None:
        """
        Find a holding snapshot by its primary key.
        """

        statement = (
            select(HoldingSnapshot)
            .where(HoldingSnapshot.id == holding_snapshot_id)
        )

        return self._scalar(statement)

    def find_by_import(
        self,
        import_id: int,
    ) -> list[HoldingSnapshot]:
        """
        Return all holding snapshots belonging to an import.
        """

        statement = (
            select(HoldingSnapshot)
            .where(HoldingSnapshot.import_id == import_id)
            .order_by(
                HoldingSnapshot.account_id,
                HoldingSnapshot.company_id,
            )
        )

        return self._list(statement)

    def find_by_account(
        self,
        account_id: int,
    ) -> list[HoldingSnapshot]:
        """
        Return all holding snapshots for an account.
        """

        statement = (
            select(HoldingSnapshot)
            .where(HoldingSnapshot.account_id == account_id)
            .order_by(HoldingSnapshot.company_id)
        )

        return self._list(statement)

    def find_by_company(
        self,
        company_id: int,
    ) -> list[HoldingSnapshot]:
        """
        Return all holding snapshots for a company.
        """

        statement = (
            select(HoldingSnapshot)
            .where(HoldingSnapshot.company_id == company_id)
            .order_by(HoldingSnapshot.import_id)
        )

        return self._list(statement)

    def find_latest_for_account(
        self,
        account_id: int,
        import_id: int,
    ) -> list[HoldingSnapshot]:
        """
        Return all holdings for an account from a specific import.
        """

        statement = (
            select(HoldingSnapshot)
            .where(HoldingSnapshot.account_id == account_id)
            .where(HoldingSnapshot.import_id == import_id)
            .order_by(HoldingSnapshot.company_id)
        )

        return self._list(statement)

    def find_latest_portfolio(
        self,
        import_id: int,
    ) -> list[HoldingSnapshot]:
        """
        Return every holding from a specific import.

        Normally this represents the current portfolio.
        """

        statement = (
            select(HoldingSnapshot)
            .where(HoldingSnapshot.import_id == import_id)
            .order_by(
                HoldingSnapshot.account_id,
                HoldingSnapshot.company_id,
            )
        )

        return self._list(statement)

    def count(
        self,
    ) -> int:
        """
        Return the total number of holding snapshots.
        """

        statement = select(func.count(HoldingSnapshot.id))

        result = self.session.scalar(statement)

        return 0 if result is None else int(result)

    def count_for_import(
        self,
        import_id: int,
    ) -> int:
        """
        Return the number of holdings in an import.
        """

        statement = (
            select(func.count(HoldingSnapshot.id))
            .where(HoldingSnapshot.import_id == import_id)
        )

        result = self.session.scalar(statement)

        return 0 if result is None else int(result)