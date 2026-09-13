"""
Read-only portfolio dashboard calculations from imported BMO snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import yfinance as yf

from src.database.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class HoldingView:
    """One holding displayed on the portfolio dashboard."""

    ticker: str
    company_name: str
    shares: Decimal
    average_cost: Decimal
    book_cost: Decimal
    statement_value: Decimal
    unrealized_gain: Decimal


@dataclass(frozen=True, slots=True)
class ValuationPoint:
    """One imported portfolio valuation displayed in the history chart."""

    valuation_date: date
    value: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioDashboard:
    """Read-only dashboard data for the latest BMO portfolio snapshot."""

    holdings: tuple[HoldingView, ...]
    history: tuple[ValuationPoint, ...]
    cash_value: Decimal
    book_cost: Decimal
    statement_value: Decimal
    unrealized_gain: Decimal
    imported_on: date | None


class PortfolioDashboardService:
    """Build read-only BMO portfolio dashboard data from snapshots."""

    ZERO = Decimal("0")

    def __init__(self, uow: UnitOfWork) -> None:
        """Initialize the service with its repository unit of work."""

        self._uow = uow

    def build(self) -> PortfolioDashboard:
        """Return the latest BMO portfolio and its import-value history."""

        imports = self._uow.imports.find_all()

        if not imports:
            return PortfolioDashboard(
                holdings=(),
                history=(),
                cash_value=self.ZERO,
                book_cost=self.ZERO,
                statement_value=self.ZERO,
                unrealized_gain=self.ZERO,
                imported_on=None,
            )

        latest_import = imports[0]
        holdings = tuple(
            sorted(
                (
                    HoldingView(
                        ticker=holding.company.ticker,
                        company_name=holding.company.company_name,
                        shares=holding.shares,
                        average_cost=holding.average_cost,
                        book_cost=holding.total_cost,
                        statement_value=holding.imported_market_value,
                        unrealized_gain=holding.imported_unrealized_gain,
                    )
                    for holding in self._uow.holdings.find_latest_portfolio(
                        latest_import.id
                    )
                ),
                key=lambda holding: holding.statement_value,
                reverse=True,
            )
        )
        cash_value = sum(
            (
                cash.cash_balance
                for cash in self._uow.cash_balances.find_latest_portfolio(
                    latest_import.id
                )
                if cash.currency == "CAD"
            ),
            start=self.ZERO,
        )
        book_cost = sum(
            (holding.book_cost for holding in holdings),
            start=self.ZERO,
        )
        statement_value = sum(
            (holding.statement_value for holding in holdings),
            start=cash_value,
        )

        return PortfolioDashboard(
            holdings=holdings,
            history=tuple(
                ValuationPoint(
                    valuation_date=import_record.import_timestamp.date(),
                    value=self._import_value(import_record.id),
                )
                for import_record in reversed(imports)
            ),
            cash_value=cash_value,
            book_cost=book_cost,
            statement_value=statement_value,
            unrealized_gain=statement_value - cash_value - book_cost,
            imported_on=latest_import.import_timestamp.date(),
        )

    def _import_value(self, import_id: int) -> Decimal:
        """Return the equity-and-CAD-cash value recorded in one import."""

        holdings_value = sum(
            (
                holding.imported_market_value
                for holding in self._uow.holdings.find_latest_portfolio(
                    import_id
                )
            ),
            start=self.ZERO,
        )
        cash_value = sum(
            (
                cash.cash_balance
                for cash in self._uow.cash_balances.find_latest_portfolio(
                    import_id
                )
                if cash.currency == "CAD"
            ),
            start=self.ZERO,
        )

        return holdings_value + cash_value
