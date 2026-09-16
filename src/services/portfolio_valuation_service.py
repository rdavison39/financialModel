"""
Service for calculating and storing current portfolio values.
"""

from collections.abc import Callable
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.holding_snapshot import HoldingSnapshot
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.services.market_price_service import MarketPrice, MarketPriceService
from src.services.portfolio_service import PortfolioService


class PortfolioValuationService:
    """Calculates and stores current portfolio values."""

    def __init__(
        self,
        session: Session,
        market_price_service: MarketPriceService | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> None:
        self.session = session
        self.portfolio_service = PortfolioService(session)
        self.market_price_service = (
            market_price_service or MarketPriceService()
        )
        self.progress_callback = progress_callback

        self._price_cache: dict[str, MarketPrice] = {}
        self._progress_total = 0
        self._progress_count = 0

        # Values calculated during the most recent update.
        self.total_daily_change = Decimal("0")
        self.total_daily_change_percent = Decimal("0")
        self.tsx_daily_change_percent: Decimal | None = None

        self.account_daily_changes: dict[int, Decimal] = {}
        self.account_daily_change_percents: dict[int, Decimal] = {}
        self.brokerage_daily_changes: dict[int, Decimal] = {}
        self.brokerage_daily_change_percents: dict[int, Decimal] = {}

    def update_account_value(self, account_id: int) -> Decimal:
        """Calculate and store today's value for an account."""
        portfolio = self.portfolio_service.get_latest_portfolio(account_id)

        if portfolio is None:
            raise ValueError(
                f"No imported portfolio exists for account {account_id}."
            )

        # This method is retained for callers that update one account.
        # It uses the same cached price logic as the bulk update.
        symbols = {"CAD=X"}
        symbols.update(holding.symbol for holding in portfolio.holdings)

        self._prepare_price_cache(symbols)

        total_value, daily_change = self._calculate_portfolio_value(
            portfolio
        )

        self._save_snapshot(
            account_id=account_id,
            snapshot_date=date.today(),
            total_value=total_value,
            daily_change=daily_change,
        )

        self.account_daily_changes[account_id] = daily_change
        self.account_daily_change_percents[account_id] = (
            self._daily_change_percent(total_value, daily_change)
        )

        return total_value

    def update_all_accounts(self) -> Decimal:
        """Calculate and store today's value for all accounts."""
        account_ids = self._get_account_ids()

        if not account_ids:
            raise ValueError("No accounts exist in the database.")

        # Load all latest imported portfolios before doing any Yahoo lookups.
        portfolios = {}

        for account_id in account_ids:
            portfolio = self.portfolio_service.get_latest_portfolio(
                account_id
            )

            if portfolio is None:
                raise ValueError(
                    f"No imported portfolio exists for account {account_id}."
                )

            portfolios[account_id] = portfolio

        # Build the complete unique lookup list.
        symbols: set[str] = {"CAD=X"}

        for portfolio in portfolios.values():
            for holding in portfolio.holdings:
                symbols.add(holding.symbol)

        # Look up each security only once.
        self._prepare_price_cache(symbols)

        # TSX is a separate market index lookup.
        tsx = self._get_price("^GSPTSE")

        if tsx.is_current:
            self.tsx_daily_change_percent = tsx.change_percent
        else:
            self.tsx_daily_change_percent = None

        self.account_daily_changes.clear()
        self.account_daily_change_percents.clear()
        self.brokerage_daily_changes.clear()
        self.brokerage_daily_change_percents.clear()

        consolidated_value = Decimal("0")
        consolidated_daily_change = Decimal("0")

        account_values: dict[int, Decimal] = {}

        for account_id in account_ids:
            total_value, daily_change = self._calculate_portfolio_value(
                portfolios[account_id]
            )

            account_values[account_id] = total_value
            consolidated_value += total_value
            consolidated_daily_change += daily_change

            self.account_daily_changes[account_id] = daily_change
            self.account_daily_change_percents[account_id] = (
                self._daily_change_percent(total_value, daily_change)
            )

            self._save_snapshot(
                account_id=account_id,
                snapshot_date=date.today(),
                total_value=total_value,
                daily_change=daily_change,
            )

        self.total_daily_change = consolidated_daily_change
        self.total_daily_change_percent = self._daily_change_percent(
            consolidated_value,
            consolidated_daily_change,
        )

        # Calculate brokerage totals and daily changes.
        from src.models.account import Account

        brokerage_values: dict[int, Decimal] = {}
        brokerage_changes: dict[int, Decimal] = {}

        for account_id, value in account_values.items():
            account = self.session.get(Account, account_id)

            if account is None:
                continue

            brokerage_values[account.brokerage_id] = (
                brokerage_values.get(
                    account.brokerage_id,
                    Decimal("0"),
                )
                + value
            )

            brokerage_changes[account.brokerage_id] = (
                brokerage_changes.get(
                    account.brokerage_id,
                    Decimal("0"),
                )
                + self.account_daily_changes[account_id]
            )

        for brokerage_id, value in brokerage_values.items():
            change = brokerage_changes[brokerage_id]

            self.brokerage_daily_changes[brokerage_id] = change
            self.brokerage_daily_change_percents[brokerage_id] = (
                self._daily_change_percent(value, change)
            )

        self._save_snapshot(
            account_id=None,
            snapshot_date=date.today(),
            total_value=consolidated_value,
            daily_change=consolidated_daily_change,
        )

        return consolidated_value

    def _prepare_price_cache(self, symbols: set[str]) -> None:
        """Retrieve all required prices once and report progress."""
        self._price_cache.clear()
        self._progress_count = 0
        self._progress_total = len(symbols)

        for symbol in sorted(symbols):
            self._get_price(symbol)

    def _get_price(self, symbol: str) -> MarketPrice:
        """Get a price from the cache or Yahoo Finance."""
        if symbol in self._price_cache:
            return self._price_cache[symbol]

        self._progress_count += 1

        if self.progress_callback is not None:
            self.progress_callback(
                self._progress_count,
                self._progress_total,
                symbol,
            )

        price = self.market_price_service.get_price(symbol)
        self._price_cache[symbol] = price

        return price

    def _calculate_portfolio_value(self, portfolio) -> tuple[Decimal, Decimal]:
        """Calculate live value and today's change using Yahoo Finance."""
        usd_to_cad = self._price_cache["CAD=X"]

        if not usd_to_cad.is_current:
            raise ValueError(
                "Could not retrieve the current USD to CAD exchange rate."
            )

        total_value = Decimal("0")
        daily_change = Decimal("0")

        for holding in portfolio.holdings:
            market_price = self._price_cache[holding.symbol]

            if market_price.is_current:
                current_price = market_price.price
                security_change = holding.quantity * market_price.change
                yahoo_previous_close = market_price.previous_close
                yahoo_change_percent = market_price.change_percent
            else:
                current_price = holding.price
                security_change = Decimal("0")
                yahoo_previous_close = Decimal("0")
                yahoo_change_percent = Decimal("0")

            value = holding.quantity * current_price

            if holding.currency == "CAD":
                value_cad = value
                change_cad = security_change
                previous_close_cad = (
                    holding.quantity * yahoo_previous_close
                )
            elif holding.currency == "USD" or holding.symbol.endswith(":US"):
                value_cad = value * usd_to_cad.price
                change_cad = security_change * usd_to_cad.price
                previous_close_cad = (
                    holding.quantity
                    * yahoo_previous_close
                    * usd_to_cad.price
                )
            else:
                raise ValueError(
                    f"Unsupported holding currency: {holding.currency}"
                )

            total_value += value_cad
            daily_change += change_cad

            # Persist live Yahoo values on the historical holding snapshot.
            # These fields are separate from the brokerage-reported fields.
            snapshot = self.session.get(
                HoldingSnapshot,
                holding.snapshot_id,
            )
            if snapshot is not None:
                snapshot.current_price = current_price
                snapshot.current_market_value = value_cad
                snapshot.current_previous_close = yahoo_previous_close
                snapshot.current_daily_change = change_cad
                snapshot.current_daily_change_percent = yahoo_change_percent

        for cash in portfolio.cash:
            if cash.currency == "CAD":
                total_value += cash.amount
            elif cash.currency == "USD":
                total_value += cash.amount * usd_to_cad.price
                if usd_to_cad.is_current:
                    daily_change += cash.amount * usd_to_cad.change
            else:
                raise ValueError(
                    f"Unsupported cash currency: {cash.currency}"
                )

        return total_value, daily_change

    @staticmethod
    def _daily_change_percent(
        current_value: Decimal,
        daily_change: Decimal,
    ) -> Decimal:
        """Calculate today's percentage change."""
        previous_close_value = current_value - daily_change

        if previous_close_value == 0:
            return Decimal("0")

        return (
            daily_change
            / previous_close_value
            * Decimal("100")
        )

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
        daily_change: Decimal,
    ) -> None:
        """Insert or replace a live Yahoo portfolio snapshot."""
        snapshot = self.session.scalar(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.account_id == account_id,
                PortfolioSnapshot.snapshot_date == snapshot_date,
            )
        )

        daily_change_percent = self._daily_change_percent(
            total_value,
            daily_change,
        )

        if snapshot is None:
            snapshot = PortfolioSnapshot(
                account_id=account_id,
                snapshot_date=snapshot_date,
                total_value=total_value,
                daily_change=daily_change,
                daily_change_percent=daily_change_percent,
            )
            self.session.add(snapshot)
        else:
            snapshot.total_value = total_value
            snapshot.daily_change = daily_change
            snapshot.daily_change_percent = daily_change_percent

        self.session.commit()

