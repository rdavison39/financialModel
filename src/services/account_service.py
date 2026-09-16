"""
Service for managing investment accounts.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.cash_snapshot import CashSnapshot
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord
from src.models.portfolio_snapshot import PortfolioSnapshot


@dataclass
class AccountSummary:
    """Summary information displayed for an investment account."""

    account_id: int
    brokerage_name: str
    account_number: str
    name: str
    current_value: Decimal | None
    cash_by_currency: dict[str, Decimal]
    holdings_count: int
    last_import: datetime | None


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

        name = name.strip()

        if not name:
            raise ValueError("Account name cannot be blank.")

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

    def get_summaries(self) -> list[AccountSummary]:
        """Return current summary information for every account."""

        accounts = list(
            self.session.execute(
                select(Account, Brokerage)
                .join(
                    Brokerage,
                    Brokerage.id == Account.brokerage_id,
                )
                .order_by(Brokerage.name, Account.account_number)
            ).all()
        )

        summaries: list[AccountSummary] = []

        for account, brokerage in accounts:
            latest_import = self.session.scalar(
                select(ImportRecord)
                .where(
                    ImportRecord.account_id == account.id,
                )
                .order_by(ImportRecord.snapshot_date.desc())
                .limit(1)
            )

            current_value = self.session.scalar(
                select(PortfolioSnapshot.total_value)
                .where(
                    PortfolioSnapshot.account_id == account.id,
                )
                .order_by(PortfolioSnapshot.snapshot_date.desc())
                .limit(1)
            )

            cash_by_currency: dict[str, Decimal] = {}
            holdings_count = 0

            if latest_import is not None:
                cash_rows = self.session.execute(
                    select(
                        CashSnapshot.currency,
                        func.sum(CashSnapshot.amount),
                    )
                    .where(
                        CashSnapshot.account_id == account.id,
                        CashSnapshot.snapshot_date
                        == latest_import.snapshot_date,
                    )
                    .group_by(CashSnapshot.currency)
                ).all()

                cash_by_currency = {
                    str(currency): amount
                    for currency, amount in cash_rows
                }

                holdings_count = int(
                    self.session.scalar(
                        select(func.count(HoldingSnapshot.id))
                        .where(
                            HoldingSnapshot.account_id == account.id,
                            HoldingSnapshot.snapshot_date
                            == latest_import.snapshot_date,
                        )
                    )
                    or 0
                )

            summaries.append(
                AccountSummary(
                    account_id=account.id,
                    brokerage_name=brokerage.name,
                    account_number=account.account_number,
                    name=account.name,
                    current_value=current_value,
                    cash_by_currency=cash_by_currency,
                    holdings_count=holdings_count,
                    last_import=(
                        latest_import.snapshot_date
                        if latest_import is not None
                        else None
                    ),
                )
            )

        return summaries

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
