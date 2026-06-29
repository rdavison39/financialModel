"""
cash_balance_snapshot_repository.py

Repository for CashBalanceSnapshot entities.

Repositories encapsulate all database access for
CashBalanceSnapshot entities.

Business logic does not belong in repositories.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy import select

from src.models.cash_balance_snapshot import CashBalanceSnapshot
from src.repositories.repository_base import RepositoryBase


class CashBalanceSnapshotRepository(
    RepositoryBase[CashBalanceSnapshot]
):
    """
    Repository for CashBalanceSnapshot entities.
    """

    def find_by_id(
        self,
        cash_balance_snapshot_id: int,
    ) -> CashBalanceSnapshot | None:
        """
        Find a cash balance snapshot by its primary key.
        """

        statement = (
            select(CashBalanceSnapshot)
            .where(
                CashBalanceSnapshot.id
                == cash_balance_snapshot_id
            )
        )

        return self._scalar(statement)

    def find_by_import(
        self,
        import_id: int,
    ) -> list[CashBalanceSnapshot]:
        """
        Return all cash balances belonging to an import.
        """

        statement = (
            select(CashBalanceSnapshot)
            .where(
                CashBalanceSnapshot.import_id
                == import_id
            )
            .order_by(
                CashBalanceSnapshot.account_id,
                CashBalanceSnapshot.currency,
            )
        )

        return self._list(statement)

    def find_by_account(
        self,
        account_id: int,
    ) -> list[CashBalanceSnapshot]:
        """
        Return all cash balances for an account.
        """

        statement = (
            select(CashBalanceSnapshot)
            .where(
                CashBalanceSnapshot.account_id
                == account_id
            )
            .order_by(
                CashBalanceSnapshot.currency,
            )
        )

        return self._list(statement)

    def find_by_account_and_currency(
        self,
        account_id: int,
        currency: str,
    ) -> CashBalanceSnapshot | None:
        """
        Return the cash balance for an account/currency.
        """

        statement = (
            select(CashBalanceSnapshot)
            .where(
                CashBalanceSnapshot.account_id
                == account_id
            )
            .where(
                CashBalanceSnapshot.currency
                == currency
            )
        )

        return self._scalar(statement)

    def find_latest_for_account(
        self,
        account_id: int,
        import_id: int,
    ) -> list[CashBalanceSnapshot]:
        """
        Return all cash balances for an account from a
        specific import.
        """

        statement = (
            select(CashBalanceSnapshot)
            .where(
                CashBalanceSnapshot.account_id
                == account_id
            )
            .where(
                CashBalanceSnapshot.import_id
                == import_id
            )
            .order_by(
                CashBalanceSnapshot.currency,
            )
        )

        return self._list(statement)

    def find_latest_portfolio(
        self,
        import_id: int,
    ) -> list[CashBalanceSnapshot]:
        """
        Return every cash balance from a specific import.
        """

        statement = (
            select(CashBalanceSnapshot)
            .where(
                CashBalanceSnapshot.import_id
                == import_id
            )
            .order_by(
                CashBalanceSnapshot.account_id,
                CashBalanceSnapshot.currency,
            )
        )

        return self._list(statement)

    def count(self) -> int:
        """
        Return the total number of cash balance snapshots.
        """

        statement = (
            select(
                func.count(
                    CashBalanceSnapshot.id
                )
            )
        )

        result = self.session.scalar(statement)

        return 0 if result is None else int(result)

    def count_for_import(
        self,
        import_id: int,
    ) -> int:
        """
        Return the number of cash balance snapshots
        in an import.
        """

        statement = (
            select(
                func.count(
                    CashBalanceSnapshot.id
                )
            )
            .where(
                CashBalanceSnapshot.import_id
                == import_id
            )
        )

        result = self.session.scalar(statement)

        return 0 if result is None else int(result)