"""
Service for managing investment accounts.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.account import Account
from src.models.brokerage import Brokerage


class AccountService:
    """Manages investment accounts."""

    def __init__(self, session: Session) -> None:
        """Initialize the account service."""
        self.session = session

    def get_or_create(
        self,
        brokerage_name: str,
        account_number: str,
        name: str | None = None,
    ) -> Account:
        """
        Find an account or create it if it does not exist.

        Accounts are uniquely identified by brokerage and account number.
        """

        brokerage = self._get_or_create_brokerage(brokerage_name)

        account = self.session.scalar(
            select(Account).where(
                Account.brokerage_id == brokerage.id,
                Account.account_number == account_number,
            )
        )

        if account is not None:
            return account

        account = Account(
            brokerage_id=brokerage.id,
            account_number=account_number,
            name=name or account_number,
        )

        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)

        return account

    def rename(
        self,
        account_id: int,
        name: str,
    ) -> Account:
        """Change the friendly name of an account."""

        account = self.session.get(Account, account_id)

        if account is None:
            raise ValueError(
                f"Account {account_id} does not exist."
            )

        account.name = name
        self.session.commit()
        self.session.refresh(account)

        return account

    def get(self, account_id: int) -> Account | None:
        """Return an account by ID."""

        return self.session.get(Account, account_id)

    def get_all(self) -> list[Account]:
        """Return all accounts."""

        return list(
            self.session.scalars(
                select(Account).order_by(Account.id)
            ).all()
        )

    def _get_or_create_brokerage(
        self,
        brokerage_name: str,
    ) -> Brokerage:
        """Find or create a brokerage."""

        brokerage = self.session.scalar(
            select(Brokerage).where(
                Brokerage.name == brokerage_name,
            )
        )

        if brokerage is not None:
            return brokerage

        brokerage = Brokerage(
            name=brokerage_name,
        )

        self.session.add(brokerage)
        self.session.commit()
        self.session.refresh(brokerage)

        return brokerage