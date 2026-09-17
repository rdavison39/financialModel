"""
Service for managing investment accounts.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
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
    account_type: str | None
    include_in_portfolio: bool
    current_value: Decimal | None
    cash_by_currency: dict[str, Decimal]
    holdings_count: int
    last_import: datetime | None


class AccountService:
    """Manages investment accounts."""

    ACCOUNT_TYPES = ("RRSP", "RESP", "TFSA", "Trust", "Margin")

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_or_create(
        self,
        brokerage_name: str,
        account_number: str,
        name: str | None = None,
    ) -> Account:
        """Find an account or create it if it does not exist."""
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
            include_in_portfolio=True,
        )
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)
        return account

    def rename(self, account_id: int, name: str) -> Account:
        """Change the friendly name of an account."""
        name = name.strip()
        if not name:
            raise ValueError("Account name cannot be blank.")

        account = self.session.get(Account, account_id)
        if account is None:
            raise ValueError(f"Account {account_id} does not exist.")

        account.name = name
        self.session.commit()
        self.session.refresh(account)
        return account

    def update_settings(
        self,
        account_id: int,
        account_type: str | None,
        include_in_portfolio: bool,
    ) -> Account:
        """Update the classification and portfolio inclusion for an account."""
        if account_type == "":
            account_type = None

        if account_type is not None and account_type not in self.ACCOUNT_TYPES:
            raise ValueError(
                f"Invalid account type: {account_type}. "
                f"Expected one of: {', '.join(self.ACCOUNT_TYPES)}."
            )

        account = self.session.get(Account, account_id)
        if account is None:
            raise ValueError(f"Account {account_id} does not exist.")

        account.account_type = account_type
        account.include_in_portfolio = bool(include_in_portfolio)
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
        """
        Return account summaries.

        Current value comes from today's PortfolioSnapshot when one exists,
        which is the same saved valuation used by the Portfolio page. If
        today's valuation has not been run, the most recent stored snapshot
        is used.
        """
        accounts = list(
            self.session.execute(
                select(Account, Brokerage)
                .join(
                    Brokerage,
                    Brokerage.id == Account.brokerage_id,
                )
                .order_by(
                    Brokerage.name,
                    Account.account_number,
                )
            ).all()
        )

        today = date.today()
        summaries: list[AccountSummary] = []

        for account, brokerage in accounts:
            latest_import = self.session.scalar(
                select(ImportRecord)
                .where(ImportRecord.account_id == account.id)
                .order_by(ImportRecord.snapshot_date.desc())
                .limit(1)
            )

            current_value = self.session.scalar(
                select(PortfolioSnapshot.total_value)
                .where(
                    PortfolioSnapshot.account_id == account.id,
                    PortfolioSnapshot.snapshot_date == today,
                )
                .order_by(
                    PortfolioSnapshot.snapshot_date.desc(),
                    PortfolioSnapshot.id.desc(),
                )
                .limit(1)
            )

            if current_value is None:
                current_value = self.session.scalar(
                    select(PortfolioSnapshot.total_value)
                    .where(PortfolioSnapshot.account_id == account.id)
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
                    str(currency): Decimal(str(amount or 0))
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
                    account_type=account.account_type,
                    include_in_portfolio=account.include_in_portfolio,
                    current_value=(
                        Decimal(str(current_value))
                        if current_value is not None
                        else None
                    ),
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

        brokerage = Brokerage(name=brokerage_name)
        self.session.add(brokerage)
        self.session.commit()
        self.session.refresh(brokerage)
        return brokerage
