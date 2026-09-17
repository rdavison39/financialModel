"""
Service for calculating and storing current portfolio values.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.portfolio_snapshot import PortfolioSnapshot
from src.services.market_price_service import MarketPrice, MarketPriceService
from src.services.portfolio_service import PortfolioService


@dataclass
class CurrentHolding:
    """A holding with its current calculated valuation."""

    symbol: str
    company_name: str
    quantity: Decimal
    price: Decimal
    market_value: Decimal
    currency: str
    average_cost: Decimal | None
    unrealized_gain: Decimal | None
    unrealized_gain_percent: Decimal | None
    daily_change: Decimal | None
    daily_change_percent: Decimal | None
    previous_close: Decimal | None
    is_current: bool = True

    @property
    def current_price(self) -> Decimal:
        """Compatibility alias used by the Holdings UI."""
        return self.price

    @property
    def current_market_value(self) -> Decimal:
        """Compatibility alias used by the Holdings UI."""
        return self.market_value

    @property
    def current_cad_value(self) -> Decimal:
        """Compatibility alias for the CAD market value."""
        return self.market_value


@dataclass
class CurrentCash:
    """Cash with its current CAD valuation."""

    currency: str
    amount: Decimal
    current_cad_value: Decimal

    @property
    def current_value(self) -> Decimal:
        """Compatibility alias for current CAD value."""
        return self.current_cad_value


class PortfolioValuationService:
    """Calculate and store current portfolio values."""

    OPTION_MULTIPLIER = Decimal("100")

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

        self.total_daily_change = Decimal("0")
        self.total_daily_change_percent = Decimal("0")
        self.tsx_daily_change_percent: Decimal | None = None

        self.account_daily_changes: dict[int, Decimal] = {}
        self.account_daily_change_percents: dict[int, Decimal] = {}
        self.brokerage_daily_changes: dict[int, Decimal] = {}
        self.brokerage_daily_change_percents: dict[int, Decimal] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_current_values(
        self,
        portfolio,
    ) -> tuple[
        list[CurrentHolding],
        list[CurrentCash],
        Decimal,
        Decimal,
    ]:
        """
        Calculate current values for an account.

        Returns:
            current holdings,
            current cash,
            total current CAD value,
            total daily change.
        """
        symbols = {"CAD=X"}
        symbols.update(
            holding.symbol for holding in portfolio.holdings
        )
        self._prepare_price_cache(symbols)

        total_value, daily_change = self._calculate_portfolio_value(
            portfolio
        )

        usd_to_cad = self._price_cache["CAD=X"]
        current_holdings: list[CurrentHolding] = []

        for holding in portfolio.holdings:
            market_price = self._price_cache[holding.symbol]

            if market_price.is_current:
                current_price = market_price.price
                multiplier = self._contract_multiplier(
                    holding.symbol
                )

                native_value = (
                    holding.quantity
                    * current_price
                    * multiplier
                )

                if (
                    holding.currency == "USD"
                    or holding.symbol.endswith(":US")
                ):
                    current_cad_value = (
                        native_value * usd_to_cad.price
                    )
                elif holding.currency == "CAD":
                    current_cad_value = native_value
                else:
                    raise ValueError(
                        f"Unsupported holding currency: "
                        f"{holding.currency}"
                    )

                previous_close = market_price.previous_close
            else:
                # Brokerage market_value is already CAD and includes
                # brokerage FX conversion and option contract sizing.
                current_cad_value = holding.market_value
                current_price = holding.price
                previous_close = holding.previous_close

            current_holdings.append(
                CurrentHolding(
                    symbol=holding.symbol,
                    company_name=holding.company_name,
                    quantity=holding.quantity,
                    price=current_price,
                    market_value=current_cad_value,
                    currency=holding.currency,
                    average_cost=holding.average_cost,
                    unrealized_gain=holding.unrealized_gain,
                    unrealized_gain_percent=(
                        holding.unrealized_gain_percent
                    ),
                    daily_change=holding.daily_change,
                    daily_change_percent=(
                        holding.daily_change_percent
                    ),
                    previous_close=previous_close,
                    is_current=market_price.is_current,
                )
            )

        current_cash: list[CurrentCash] = []

        for cash in portfolio.cash:
            if cash.currency == "CAD":
                current_cad_value = cash.amount
            elif cash.currency == "USD":
                current_cad_value = (
                    cash.amount * usd_to_cad.price
                )
            else:
                raise ValueError(
                    f"Unsupported cash currency: {cash.currency}"
                )

            current_cash.append(
                CurrentCash(
                    currency=cash.currency,
                    amount=cash.amount,
                    current_cad_value=current_cad_value,
                )
            )

        return (
            current_holdings,
            current_cash,
            total_value,
            daily_change,
        )

    def update_account_value(self, account_id: int) -> Decimal:
        """Calculate and store today's value for one account."""
        portfolio = self.portfolio_service.get_latest_portfolio(
            account_id
        )

        if portfolio is None:
            raise ValueError(
                f"No imported portfolio exists for account "
                f"{account_id}."
            )

        symbols = {"CAD=X"}
        symbols.update(
            holding.symbol for holding in portfolio.holdings
        )
        self._prepare_price_cache(symbols)

        total_value, daily_change = self._calculate_portfolio_value(
            portfolio
        )

        self._save_snapshot(
            account_id=account_id,
            snapshot_date=date.today(),
            total_value=total_value,
        )

        self.account_daily_changes[account_id] = daily_change
        self.account_daily_change_percents[account_id] = (
            self._daily_change_percent(
                total_value,
                daily_change,
            )
        )

        return total_value

    def update_all_accounts(self) -> Decimal:
        """Calculate and store today's value for all accounts."""
        account_ids = self._get_account_ids()

        if not account_ids:
            raise ValueError("No accounts exist in the database.")

        portfolios = {}

        for account_id in account_ids:
            portfolio = self.portfolio_service.get_latest_portfolio(
                account_id
            )

            if portfolio is None:
                raise ValueError(
                    f"No imported portfolio exists for account "
                    f"{account_id}."
                )

            portfolios[account_id] = portfolio

        symbols: set[str] = {"CAD=X"}

        for portfolio in portfolios.values():
            symbols.update(
                holding.symbol
                for holding in portfolio.holdings
            )

        self._prepare_price_cache(symbols)

        tsx = self._get_price("^GSPTSE")

        self.tsx_daily_change_percent = (
            tsx.change_percent
            if tsx.is_current
            else None
        )

        self.account_daily_changes.clear()
        self.account_daily_change_percents.clear()
        self.brokerage_daily_changes.clear()
        self.brokerage_daily_change_percents.clear()

        consolidated_value = Decimal("0")
        consolidated_daily_change = Decimal("0")
        account_values: dict[int, Decimal] = {}

        for account_id in account_ids:
            total_value, daily_change = (
                self._calculate_portfolio_value(
                    portfolios[account_id]
                )
            )

            account_values[account_id] = total_value
            consolidated_value += total_value
            consolidated_daily_change += daily_change

            self.account_daily_changes[account_id] = daily_change
            self.account_daily_change_percents[account_id] = (
                self._daily_change_percent(
                    total_value,
                    daily_change,
                )
            )

            self._save_snapshot(
                account_id=account_id,
                snapshot_date=date.today(),
                total_value=total_value,
            )

        self.total_daily_change = consolidated_daily_change
        self.total_daily_change_percent = (
            self._daily_change_percent(
                consolidated_value,
                consolidated_daily_change,
            )
        )

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
        )

        return consolidated_value

    # ------------------------------------------------------------------
    # Price cache
    # ------------------------------------------------------------------

    def _prepare_price_cache(self, symbols: set[str]) -> None:
        self._price_cache.clear()
        self._progress_count = 0
        self._progress_total = len(symbols)

        for symbol in sorted(symbols):
            self._get_price(symbol)

    def _get_price(self, symbol: str) -> MarketPrice:
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

    # ------------------------------------------------------------------
    # Valuation
    # ------------------------------------------------------------------

    @classmethod
    def _is_option(cls, symbol: str) -> bool:
        normalized = symbol.strip().upper()
        return (
            normalized.startswith("CALL ")
            or normalized.startswith("PUT ")
        )

    @classmethod
    def _contract_multiplier(cls, symbol: str) -> Decimal:
        if cls._is_option(symbol):
            return cls.OPTION_MULTIPLIER

        return Decimal("1")

    def _calculate_portfolio_value(
        self,
        portfolio,
    ) -> tuple[Decimal, Decimal]:
        """Calculate current CAD value and daily change."""
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
                native_value = (
                    holding.quantity
                    * market_price.price
                    * self._contract_multiplier(holding.symbol)
                )

                if (
                    holding.currency == "USD"
                    or holding.symbol.endswith(":US")
                ):
                    value = native_value * usd_to_cad.price
                elif holding.currency == "CAD":
                    value = native_value
                else:
                    raise ValueError(
                        f"Unsupported holding currency: "
                        f"{holding.currency}"
                    )
            else:
                # Brokerage market_value is already CAD.
                value = holding.market_value

            holding_change = holding.daily_change or Decimal("0")

            if (
                holding.currency == "USD"
                or holding.symbol.endswith(":US")
            ):
                daily_change += (
                    holding_change * usd_to_cad.price
                )
            elif holding.currency == "CAD":
                daily_change += holding_change
            else:
                raise ValueError(
                    f"Unsupported holding currency: "
                    f"{holding.currency}"
                )

            total_value += value

        for cash in portfolio.cash:
            if cash.currency == "CAD":
                total_value += cash.amount
            elif cash.currency == "USD":
                total_value += cash.amount * usd_to_cad.price
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
        previous_close_value = current_value - daily_change

        if previous_close_value == 0:
            return Decimal("0")

        return (
            daily_change
            / previous_close_value
            * Decimal("100")
        )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    def _get_account_ids(self) -> list[int]:
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
