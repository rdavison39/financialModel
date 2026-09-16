"""
Service for calculating and storing current portfolio values.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.portfolio_snapshot import PortfolioSnapshot
from src.services.market_price_service import MarketPriceService
from src.services.portfolio_service import PortfolioService


class PortfolioValuationService:
    """Calculates and stores current portfolio values."""

    def __init__(
        self,
        session: Session,
        market_price_service: MarketPriceService | None = None,
    ) -> None:
        """Initialize the valuation service."""
        self.session = session
        self.portfolio_service = PortfolioService(session)
        self.market_price_service = (
            market_price_service or MarketPriceService()
        )

    def update_account_value(
        self,
        account_id: int,
    ) -> Decimal:
        """Calculate and store today's value for an account."""

        portfolio = self.portfolio_service.get_latest_portfolio(
            account_id
        )

        if portfolio is None:
            raise ValueError(
                f"No imported portfolio exists for account {account_id}."
            )

        total_value = Decimal("0")

        usd_to_cad = self.market_price_service.get_price("CAD=X")

        if not usd_to_cad.is_current:
            raise ValueError(
                "Could not retrieve the current USD to CAD exchange rate."
            )

        for holding in portfolio.holdings:
            market_price = self.market_price_service.get_price(
                holding.symbol
            )

            if market_price.is_current:
                current_price = market_price.price
            else:
                current_price = holding.price

            value = holding.quantity * current_price

            if holding.currency == "CAD":
                total_value += value
            elif holding.symbol.endswith(":US"):
                total_value += value * usd_to_cad.price
            else:
                raise ValueError(
                    f"Unsupported holding currency: {holding.currency}"
                )

        for cash in portfolio.cash:
            if cash.currency == "CAD":
                total_value += cash.amount
            elif cash.currency == "USD":
                total_value += cash.amount * usd_to_cad.price
            else:
                raise ValueError(
                    f"Unsupported cash currency: {cash.currency}"
                )

        self._save_snapshot(
            account_id=account_id,
            snapshot_date=date.today(),
            total_value=total_value,
        )

        return total_value

    def update_all_accounts(self) -> Decimal:
        """Calculate and store today's value for all accounts."""

        account_ids = self._get_account_ids()

        if not account_ids:
            raise ValueError("No accounts exist in the database.")

        consolidated_value = Decimal("0")

        for account_id in account_ids:
            account_value = self.update_account_value(account_id)
            consolidated_value += account_value

        self._save_snapshot(
            account_id=None,
            snapshot_date=date.today(),
            total_value=consolidated_value,
        )

        return consolidated_value

    def _get_account_ids(self) -> list[int]:
        """Return the IDs of all accounts."""

        from src.models.account import Account

        return list(
            self.session.scalars(
                select(Account.id).order_by(Account.id)
            ).all()
        )

    def _save_snapshot(
        self,
        account_id: int | None,
        snapshot_date: date,
        total_value: Decimal,
    ) -> None:
        """Insert or replace a daily portfolio snapshot."""

        snapshot = self.session.scalar(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.account_id == account_id,
                PortfolioSnapshot.snapshot_date == snapshot_date,
            )
        )

        if snapshot is None:
            snapshot = PortfolioSnapshot(
                account_id=account_id,
                snapshot_date=snapshot_date,
                total_value=total_value,
            )
            self.session.add(snapshot)
        else:
            snapshot.total_value = total_value

        self.session.commit()