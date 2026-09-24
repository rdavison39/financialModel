"""Historical account comparison data service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.portfolio_snapshot import PortfolioSnapshot


@dataclass(frozen=True)
class AccountComparison:
    """Account identity used by the comparison screen."""

    account_id: int
    brokerage_name: str
    account_number: str
    account_name: str

    @property
    def label(self) -> str:
        """Return the full account label used in the UI."""
        return (
            f"{self.brokerage_name} - "
            f"{self.account_number} - "
            f"{self.account_name}"
        )


@dataclass(frozen=True)
class AccountHistoryPoint:
    """One historical valuation and market-day performance for one account."""

    account_id: int
    snapshot_date: date
    total_value: Decimal
    daily_change: Decimal | None = None
    daily_change_percent: Decimal | None = None


class AccountComparisonHistoryService:
    """Load account histories for multi-line comparison charts."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_accounts(self) -> list[AccountComparison]:
        """Return all accounts ordered by brokerage and account number."""
        rows = self.session.execute(
            select(Account, Brokerage)
            .join(Brokerage, Brokerage.id == Account.brokerage_id)
            .order_by(Brokerage.name, Account.account_number)
        ).all()

        return [
            AccountComparison(
                account_id=account.id,
                brokerage_name=brokerage.name,
                account_number=account.account_number,
                account_name=account.name,
            )
            for account, brokerage in rows
        ]

    def get_histories(
        self,
        account_ids: list[int],
        start_date: date,
        end_date: date,
    ) -> dict[int, list[AccountHistoryPoint]]:
        """Return snapshot histories for selected accounts."""
        if start_date > end_date or not account_ids:
            return {}

        unique_ids = list(dict.fromkeys(account_ids))

        rows = self.session.execute(
            select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.account_id.in_(unique_ids),
                PortfolioSnapshot.snapshot_date >= start_date,
                PortfolioSnapshot.snapshot_date <= end_date,
            )
            .order_by(
                PortfolioSnapshot.account_id,
                PortfolioSnapshot.snapshot_date,
                PortfolioSnapshot.id,
            )
        ).scalars().all()

        histories: dict[int, list[AccountHistoryPoint]] = {
            account_id: [] for account_id in unique_ids
        }

        for row in rows:
            if row.account_id is None:
                continue

            histories.setdefault(row.account_id, []).append(
                AccountHistoryPoint(
                    account_id=row.account_id,
                    snapshot_date=row.snapshot_date,
                    total_value=Decimal(str(row.total_value)),
                    daily_change=(
                        Decimal(str(row.daily_change))
                        if row.daily_change is not None
                        else None
                    ),
                    daily_change_percent=(
                        Decimal(str(row.daily_change_percent))
                        if row.daily_change_percent is not None
                        else None
                    ),
                )
            )

        return histories
