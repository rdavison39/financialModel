"""
Service for calculating and storing current portfolio values.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
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

        Price data is read from the in-memory cache when it has already been
        prepared by update_all_accounts(). Otherwise the cache is populated
        here. This keeps the public method useful while avoiding duplicate
        Yahoo requests during a portfolio update.
        """
        symbols = {"CAD=X"}
        symbols.update(
            holding.symbol for holding in portfolio.holdings
        )

        if not symbols.issubset(self._price_cache):
            self._prepare_price_cache(symbols)

        total_value, daily_change = self._calculate_portfolio_value(
            portfolio
        )

        usd_to_cad = self._price_cache["CAD=X"]
        current_holdings: list[CurrentHolding] = []

        for holding in portfolio.holdings:
            market_price = self._price_cache[holding.symbol]
            multiplier = self._contract_multiplier(holding.symbol)

            if market_price.is_current:
                current_price = market_price.price
                previous_close = market_price.previous_close
                native_value = (
                    holding.quantity
                    * current_price
                    * multiplier
                )

                if (
                    holding.currency == "USD"
                    or holding.symbol.endswith(":US")
                ):
                    current_cad_value = native_value * usd_to_cad.price
                elif holding.currency == "CAD":
                    current_cad_value = native_value
                else:
                    raise ValueError(
                        f"Unsupported holding currency: {holding.currency}"
                    )

                position_daily_change = self._calculate_holding_daily_change(
                    holding, market_price, usd_to_cad.price
                )
                position_daily_change_percent = (
                    self._calculate_holding_daily_change_percent(
                        holding, market_price, usd_to_cad.price
                    )
                )
            else:
                current_cad_value = holding.market_value
                current_price = holding.price
                previous_close = holding.previous_close
                position_daily_change = holding.daily_change or Decimal("0")
                position_daily_change_percent = holding.daily_change_percent

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
                    unrealized_gain_percent=holding.unrealized_gain_percent,
                    daily_change=position_daily_change,
                    daily_change_percent=position_daily_change_percent,
                    previous_close=previous_close,
                    is_current=market_price.is_current,
                )
            )

        current_cash: list[CurrentCash] = []
        for cash in portfolio.cash:
            if cash.currency == "CAD":
                current_cad_value = cash.amount
            elif cash.currency == "USD":
                current_cad_value = cash.amount * usd_to_cad.price
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
        """Calculate, cache, and store today's value for one account."""
        portfolio = self.portfolio_service.get_latest_portfolio(account_id)

        if portfolio is None:
            raise ValueError(
                f"No imported portfolio exists for account {account_id}."
            )

        symbols = {"CAD=X"}
        symbols.update(holding.symbol for holding in portfolio.holdings)
        self._prepare_price_cache(symbols)

        (
            current_holdings,
            current_cash,
            total_value,
            daily_change,
        ) = self.calculate_current_values(portfolio)

        updated_at = datetime.now()
        self._save_snapshot(
            account_id=account_id,
            snapshot_date=date.today(),
            total_value=total_value,
            daily_change=daily_change,
            daily_change_percent=self._daily_change_percent(
                total_value,
                daily_change,
            ),
            tsx_daily_change_percent=self.tsx_daily_change_percent,
            usd_to_cad=self._price_cache["CAD=X"].price,
            valuation_updated_at=updated_at,
            current_holdings=current_holdings,
            current_cash=current_cash,
        )

        self.account_daily_changes[account_id] = daily_change
        self.account_daily_change_percents[account_id] = (
            self._daily_change_percent(total_value, daily_change)
        )

        return total_value

    def update_all_accounts(self) -> Decimal:
        """Calculate, cache, and store today's values for all accounts."""
        account_ids = self._get_account_ids()

        if not account_ids:
            raise ValueError("No accounts exist in the database.")

        portfolios = {}
        for account_id in account_ids:
            portfolio = self.portfolio_service.get_latest_portfolio(account_id)
            if portfolio is None:
                raise ValueError(
                    f"No imported portfolio exists for account {account_id}."
                )
            portfolios[account_id] = portfolio

        symbols: set[str] = {"CAD=X", "^GSPTSE"}
        for portfolio in portfolios.values():
            symbols.update(holding.symbol for holding in portfolio.holdings)

        self._prepare_price_cache(symbols)

        tsx = self._get_price("^GSPTSE")
        self.tsx_daily_change_percent = (
            tsx.change_percent if tsx.is_current else None
        )

        self.account_daily_changes.clear()
        self.account_daily_change_percents.clear()
        self.brokerage_daily_changes.clear()
        self.brokerage_daily_change_percents.clear()

        consolidated_value = Decimal("0")
        consolidated_daily_change = Decimal("0")
        account_values: dict[int, Decimal] = {}
        account_current_values: dict[
            int,
            tuple[list[CurrentHolding], list[CurrentCash], Decimal, Decimal],
        ] = {}

        updated_at = datetime.now()

        from src.models.account import Account

        for account_id, portfolio in portfolios.items():
            (
                current_holdings,
                current_cash,
                total_value,
                daily_change,
            ) = self.calculate_current_values(portfolio)

            account = self.session.get(Account, account_id)
            include_in_portfolio = (
                account is not None and account.include_in_portfolio
            )

            account_values[account_id] = total_value

            if include_in_portfolio:
                consolidated_value += total_value
                consolidated_daily_change += daily_change

            self.account_daily_changes[account_id] = daily_change
            self.account_daily_change_percents[account_id] = (
                self._daily_change_percent(total_value, daily_change)
            )

            account_current_values[account_id] = (
                current_holdings,
                current_cash,
                total_value,
                daily_change,
            )

            self._save_snapshot(
                account_id=account_id,
                snapshot_date=date.today(),
                total_value=total_value,
                daily_change=daily_change,
                daily_change_percent=self.account_daily_change_percents[
                    account_id
                ],
                tsx_daily_change_percent=self.tsx_daily_change_percent,
                usd_to_cad=self._price_cache["CAD=X"].price,
                valuation_updated_at=updated_at,
                current_holdings=current_holdings,
                current_cash=current_cash,
            )

        self.total_daily_change = consolidated_daily_change
        self.total_daily_change_percent = self._daily_change_percent(
            consolidated_value,
            consolidated_daily_change,
        )

        brokerage_values: dict[int, Decimal] = {}
        brokerage_changes: dict[int, Decimal] = {}

        for account_id, value in account_values.items():
            account = self.session.get(Account, account_id)
            if account is None or not account.include_in_portfolio:
                continue

            brokerage_values[account.brokerage_id] = (
                brokerage_values.get(account.brokerage_id, Decimal("0"))
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

        consolidated_holdings: list[CurrentHolding] = []
        consolidated_cash: list[CurrentCash] = []
        for account_id, (
            current_holdings,
            current_cash,
            _,
            _,
        ) in account_current_values.items():
            account = self.session.get(Account, account_id)
            if account is None or not account.include_in_portfolio:
                continue

            consolidated_holdings.extend(current_holdings)
            consolidated_cash.extend(current_cash)

        self._save_snapshot(
            account_id=None,
            snapshot_date=date.today(),
            total_value=consolidated_value,
            daily_change=consolidated_daily_change,
            daily_change_percent=self.total_daily_change_percent,
            tsx_daily_change_percent=self.tsx_daily_change_percent,
            usd_to_cad=self._price_cache["CAD=X"].price,
            valuation_updated_at=updated_at,
            current_holdings=consolidated_holdings,
            current_cash=consolidated_cash,
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

            if market_price.is_current:
                daily_change += self._calculate_holding_daily_change(
                    holding, market_price, usd_to_cad.price
                )
            else:
                # Yahoo-unavailable securities retain the brokerage-imported
                # daily change as a fallback.
                holding_change = holding.daily_change or Decimal("0")
                if (
                    holding.currency == "USD"
                    or holding.symbol.endswith(":US")
                ):
                    daily_change += holding_change * usd_to_cad.price
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

    @classmethod
    def _calculate_holding_daily_change(
        cls,
        holding,
        market_price: MarketPrice,
        usd_to_cad: Decimal,
    ) -> Decimal:
        """Calculate a holding's change from its current quote movement."""
        if not market_price.is_current or market_price.previous_close is None:
            return Decimal("0")

        position_change = (
            holding.quantity
            * (market_price.price - market_price.previous_close)
            * cls._contract_multiplier(holding.symbol)
        )

        if holding.currency == "USD" or holding.symbol.endswith(":US"):
            return position_change * usd_to_cad
        if holding.currency == "CAD":
            return position_change

        raise ValueError(
            f"Unsupported holding currency: {holding.currency}"
        )

    @classmethod
    def _calculate_holding_daily_change_percent(
        cls,
        holding,
        market_price: MarketPrice,
        usd_to_cad: Decimal,
    ) -> Decimal | None:
        """Calculate a holding's daily percentage change."""
        if not market_price.is_current or market_price.previous_close is None:
            return holding.daily_change_percent

        previous_value = (
            holding.quantity
            * market_price.previous_close
            * cls._contract_multiplier(holding.symbol)
        )
        if holding.currency == "USD" or holding.symbol.endswith(":US"):
            previous_value *= usd_to_cad
        elif holding.currency != "CAD":
            raise ValueError(
                f"Unsupported holding currency: {holding.currency}"
            )

        if previous_value == 0:
            return Decimal("0")

        change = cls._calculate_holding_daily_change(
            holding, market_price, usd_to_cad
        )
        return change / previous_value * Decimal("100")

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
        daily_change: Decimal,
        daily_change_percent: Decimal,
        tsx_daily_change_percent: Decimal | None,
        usd_to_cad: Decimal,
        valuation_updated_at: datetime,
        current_holdings: list[CurrentHolding],
        current_cash: list[CurrentCash],
    ) -> None:
        """Insert or replace a daily valuation snapshot and its cached data."""
        snapshot = self.session.scalar(
            select(PortfolioSnapshot).where(
                PortfolioSnapshot.account_id == account_id,
                PortfolioSnapshot.snapshot_date == snapshot_date,
            )
        )

        valuation_data = {
            "holdings": [
                {
                    "symbol": item.symbol,
                    "company_name": item.company_name,
                    "quantity": str(item.quantity),
                    "price": str(item.price),
                    "market_value": str(item.market_value),
                    "currency": item.currency,
                    "average_cost": (
                        str(item.average_cost)
                        if item.average_cost is not None
                        else None
                    ),
                    "unrealized_gain": (
                        str(item.unrealized_gain)
                        if item.unrealized_gain is not None
                        else None
                    ),
                    "unrealized_gain_percent": (
                        str(item.unrealized_gain_percent)
                        if item.unrealized_gain_percent is not None
                        else None
                    ),
                    "daily_change": (
                        str(item.daily_change)
                        if item.daily_change is not None
                        else None
                    ),
                    "daily_change_percent": (
                        str(item.daily_change_percent)
                        if item.daily_change_percent is not None
                        else None
                    ),
                    "previous_close": (
                        str(item.previous_close)
                        if item.previous_close is not None
                        else None
                    ),
                    "is_current": item.is_current,
                }
                for item in current_holdings
            ],
            "cash": [
                {
                    "currency": item.currency,
                    "amount": str(item.amount),
                    "current_cad_value": str(item.current_cad_value),
                }
                for item in current_cash
            ],
        }

        if snapshot is None:
            snapshot = PortfolioSnapshot(
                account_id=account_id,
                snapshot_date=snapshot_date,
                total_value=total_value,
            )
            self.session.add(snapshot)

        snapshot.total_value = total_value
        snapshot.daily_change = daily_change
        snapshot.daily_change_percent = daily_change_percent
        snapshot.tsx_daily_change_percent = tsx_daily_change_percent
        snapshot.usd_to_cad = usd_to_cad
        snapshot.valuation_updated_at = valuation_updated_at
        snapshot.valuation_data = json.dumps(valuation_data)

        self.session.commit()

    def get_cached_current_values(
        self,
        account_id: int,
    ) -> tuple[
        list[CurrentHolding],
        list[CurrentCash],
        Decimal,
        Decimal,
    ] | None:
        """
        Return the most recently cached valuation for an account.

        This method performs database reads only. It never contacts Yahoo
        Finance, which makes opening the Account Holdings window immediate.
        """
        snapshot = self.session.scalar(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.account_id == account_id)
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .limit(1)
        )

        if snapshot is None or not snapshot.valuation_data:
            return None

        data = json.loads(snapshot.valuation_data)

        holdings = [
            CurrentHolding(
                symbol=item["symbol"],
                company_name=item["company_name"],
                quantity=Decimal(item["quantity"]),
                price=Decimal(item["price"]),
                market_value=Decimal(item["market_value"]),
                currency=item["currency"],
                average_cost=(
                    Decimal(item["average_cost"])
                    if item["average_cost"] is not None
                    else None
                ),
                unrealized_gain=(
                    Decimal(item["unrealized_gain"])
                    if item["unrealized_gain"] is not None
                    else None
                ),
                unrealized_gain_percent=(
                    Decimal(item["unrealized_gain_percent"])
                    if item["unrealized_gain_percent"] is not None
                    else None
                ),
                daily_change=(
                    Decimal(item["daily_change"])
                    if item["daily_change"] is not None
                    else None
                ),
                daily_change_percent=(
                    Decimal(item["daily_change_percent"])
                    if item["daily_change_percent"] is not None
                    else None
                ),
                previous_close=(
                    Decimal(item["previous_close"])
                    if item["previous_close"] is not None
                    else None
                ),
                is_current=bool(item["is_current"]),
            )
            for item in data.get("holdings", [])
        ]

        cash = [
            CurrentCash(
                currency=item["currency"],
                amount=Decimal(item["amount"]),
                current_cad_value=Decimal(item["current_cad_value"]),
            )
            for item in data.get("cash", [])
        ]

        daily_change = (
            Decimal(str(snapshot.daily_change))
            if snapshot.daily_change is not None
            else Decimal("0")
        )

        return holdings, cash, Decimal(str(snapshot.total_value)), daily_change

