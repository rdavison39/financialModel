"""
Services for retrieving current portfolio holdings and cash.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.account import Account
from src.models.cash_snapshot import CashSnapshot
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord


@dataclass
class PortfolioHolding:
    """A holding from an account snapshot."""

    symbol: str
    company_name: str
    quantity: Decimal
    price: Decimal
    market_value: Decimal
    currency: str


@dataclass
class PortfolioCash:
    """Cash from an account snapshot."""

    currency: str
    amount: Decimal


@dataclass
class AccountPortfolio:
    """Portfolio state for an account."""

    account_id: int
    snapshot_date: datetime
    holdings: list[PortfolioHolding]
    cash: list[PortfolioCash]


class PortfolioService:
    """Retrieves portfolio information for accounts."""

    def __init__(self, session: Session) -> None:
        """Initialize the portfolio service."""
        self.session = session

    def get_latest_portfolio(
        self,
        account_id: int,
    ) -> AccountPortfolio | None:
        """Return the latest complete imported snapshot."""

        latest_import = self.session.scalar(
            select(ImportRecord)
            .where(ImportRecord.account_id == account_id)
            .order_by(ImportRecord.snapshot_date.desc())
            .limit(1)
        )

        if latest_import is None:
            return None

        snapshot_date = latest_import.snapshot_date

        holding_rows = self.session.execute(
            select(HoldingSnapshot, Company)
            .join(
                Company,
                Company.id == HoldingSnapshot.company_id,
            )
            .where(
                HoldingSnapshot.account_id == account_id,
                HoldingSnapshot.snapshot_date == snapshot_date,
            )
        ).all()

        cash_rows = self.session.scalars(
            select(CashSnapshot).where(
                CashSnapshot.account_id == account_id,
                CashSnapshot.snapshot_date == snapshot_date,
            )
        ).all()

        holdings = [
            PortfolioHolding(
                symbol=company.symbol,
                company_name=company.name,
                quantity=holding.quantity,
                price=holding.price,
                market_value=holding.market_value,
                currency=holding.currency,
            )
            for holding, company in holding_rows
        ]

        cash = [
            PortfolioCash(
                currency=item.currency,
                amount=item.amount,
            )
            for item in cash_rows
        ]

        return AccountPortfolio(
            account_id=account_id,
            snapshot_date=snapshot_date,
            holdings=holdings,
            cash=cash,
        )