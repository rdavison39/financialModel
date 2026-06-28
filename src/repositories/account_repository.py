"""
account_repository.py

Repository for Account entities.

Repositories encapsulate all database access for Account entities.

Business logic does not belong in repositories.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy import select

from src.models.account import Account
from src.repositories.repository_base import RepositoryBase


class AccountRepository(RepositoryBase[Account]):
    """
    Repository for Account entities.
    """

    def find_by_id(
        self,
        account_id: int,
    ) -> Account | None:
        """
        Find an account by its primary key.
        """

        statement = (
            select(Account)
            .where(Account.id == account_id)
        )

        return self._scalar(statement)

    def find_by_account_number(
        self,
        brokerage_id: int,
        account_number: str,
    ) -> Account | None:
        """
        Find an account using the brokerage/account number combination.
        """

        statement = (
            select(Account)
            .where(Account.brokerage_id == brokerage_id)
            .where(Account.account_number == account_number)
        )

        return self._scalar(statement)

    def find_by_owner(
        self,
        owner: str,
    ) -> list[Account]:
        """
        Return all accounts belonging to an owner.
        """

        statement = (
            select(Account)
            .where(Account.owner == owner)
            .order_by(Account.account_name)
        )

        return self._list(statement)

    def find_all(self) -> list[Account]:
        """
        Return all accounts ordered by owner and account name.
        """

        statement = (
            select(Account)
            .order_by(
                Account.owner,
                Account.account_name,
            )
        )

        return self._list(statement)

    def exists(
        self,
        brokerage_id: int,
        account_number: str,
    ) -> bool:
        """
        Determine whether an account exists.
        """

        return (
            self.find_by_account_number(
                brokerage_id,
                account_number,
            )
            is not None
        )

    def count(self) -> int:
        """
        Return the total number of accounts.

        Uses SQL COUNT(*) rather than loading every row.
        """

        statement = select(func.count(Account.id))

        result = self.session.scalar(statement)

        return 0 if result is None else int(result)

    def create_if_missing(
        self,
        *,
        brokerage_id: int,
        account_number: str,
        account_name: str,
        owner: str,
        account_type: str,
        currency: str,
    ) -> Account:
        """
        Return an existing account or create a new one.

        The account is added to the current session but is not
        committed. The caller is responsible for committing the
        transaction.
        """

        account = self.find_by_account_number(
            brokerage_id,
            account_number,
        )

        if account is not None:
            return account

        account = Account(
            brokerage_id=brokerage_id,
            account_number=account_number,
            account_name=account_name,
            owner=owner,
            account_type=account_type,
            currency=currency,
            active=True,
        )

        self.add(account)

        return account