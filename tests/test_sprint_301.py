"""
Tests for Sprint 3.0.1 portfolio valuation caching.
"""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.models.base import Base
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.company import Company
from src.models.cash_snapshot import CashSnapshot
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.services.market_price_service import MarketPrice
from src.services.portfolio_valuation_service import (
    CurrentCash,
    CurrentHolding,
    PortfolioValuationService,
)


def make_session():
    """Create an isolated in-memory database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_preferred_share_conversion_is_algorithmic():
    """Canadian preferred-share symbols convert to Yahoo format."""
    service = PortfolioValuationService(make_session())

    assert (
        service.market_price_service._convert_preferred_share_symbol(
            "BPO.PR.N:CA"
        )
        == "BPO-PN.TO"
    )
    assert (
        service.market_price_service._convert_preferred_share_symbol(
            "BPO.PR.A:CA"
        )
        == "BPO-PA.TO"
    )
    assert (
        service.market_price_service._convert_preferred_share_symbol(
            "BCE.PR.M:CA"
        )
        == "BCE-PM.TO"
    )
    assert (
        service.market_price_service._convert_preferred_share_symbol(
            "BPO.PR.E:CA"
        )
        == "BPO-PE.TO"
    )
    assert (
        service.market_price_service._convert_preferred_share_symbol(
            "BPO.PR.P:CA"
        )
        == "BPO-PP.TO"
    )


def test_preferred_share_conversion_ignores_non_preferred_symbols():
    """Only the expected Canadian preferred-share pattern is converted."""
    service = PortfolioValuationService(make_session())

    assert (
        service.market_price_service._convert_preferred_share_symbol(
            "BAM:CA"
        )
        is None
    )
    assert (
        service.market_price_service._convert_preferred_share_symbol(
            "BAM.PR.N:US"
        )
        is None
    )


def test_preferred_share_candidates_include_algorithmic_conversion():
    """The algorithmic preferred-share ticker is tried after normal conversion."""
    service = PortfolioValuationService(make_session())

    candidates = service.market_price_service._yahoo_symbol_candidates(
        "BPO.PR.N:CA"
    )

    assert candidates[0] == "BPO-PR-N.TO"
    assert "BPO-PN.TO" in candidates


def test_cached_valuation_round_trips_without_market_data():
    """Calculated holdings and cash can be stored and read back."""
    session = make_session()

    try:
        service = PortfolioValuationService(session)

        holding = CurrentHolding(
            symbol="BAM:CA",
            company_name="Brookfield Asset Management",
            quantity=Decimal("100"),
            price=Decimal("72.50"),
            market_value=Decimal("7250.00"),
            currency="CAD",
            average_cost=Decimal("65.00"),
            unrealized_gain=Decimal("750.00"),
            unrealized_gain_percent=Decimal("11.538461"),
            daily_change=Decimal("25.00"),
            daily_change_percent=Decimal("0.345"),
            previous_close=Decimal("72.25"),
            is_current=True,
        )
        cash = CurrentCash(
            currency="CAD",
            amount=Decimal("1000.00"),
            current_cad_value=Decimal("1000.00"),
        )

        updated_at = datetime(2026, 9, 17, 20, 30, 15)

        service._save_snapshot(
            account_id=1,
            snapshot_date=date(2026, 9, 17),
            total_value=Decimal("8250.00"),
            daily_change=Decimal("25.00"),
            daily_change_percent=Decimal("0.304"),
            tsx_daily_change_percent=Decimal("0.63"),
            usd_to_cad=Decimal("1.3742"),
            valuation_updated_at=updated_at,
            current_holdings=[holding],
            current_cash=[cash],
        )

        cached = service.get_cached_current_values(1)

        assert cached is not None

        holdings, cash_rows, total, change = cached

        assert total == Decimal("8250.00")
        assert change == Decimal("25.00")
        assert holdings[0].symbol == "BAM:CA"
        assert holdings[0].price == Decimal("72.50")
        assert holdings[0].market_value == Decimal("7250.00")
        assert holdings[0].is_current is True
        assert cash_rows[0].current_cad_value == Decimal("1000.00")

        snapshot = session.query(PortfolioSnapshot).one()
        assert snapshot.tsx_daily_change_percent == Decimal("0.630000")
        assert snapshot.usd_to_cad == Decimal("1.37420000")
        assert snapshot.valuation_updated_at == updated_at
    finally:
        session.close()


def test_calculate_current_values_reuses_prepared_price_cache():
    """A second calculation does not call the market service again."""
    session = make_session()

    class FakeMarketPriceService:
        def __init__(self):
            self.calls = []

        def get_price(self, symbol):
            self.calls.append(symbol)
            if symbol == "CAD=X":
                return MarketPrice(
                    price=Decimal("1.37"),
                    previous_close=Decimal("1.36"),
                    change=Decimal("0.01"),
                    change_percent=Decimal("0.735294"),
                    is_current=True,
                )
            return MarketPrice(
                price=Decimal("10.00"),
                previous_close=Decimal("9.90"),
                change=Decimal("0.10"),
                change_percent=Decimal("1.010101"),
                is_current=True,
            )

    try:
        market_service = FakeMarketPriceService()
        service = PortfolioValuationService(
            session,
            market_price_service=market_service,
        )

        portfolio = SimpleNamespace(
            holdings=[
                SimpleNamespace(
                    symbol="ABC:CA",
                    company_name="ABC",
                    quantity=Decimal("10"),
                    price=Decimal("9.00"),
                    market_value=Decimal("90.00"),
                    currency="CAD",
                    average_cost=Decimal("8.00"),
                    unrealized_gain=Decimal("20.00"),
                    unrealized_gain_percent=Decimal("25.00"),
                    daily_change=Decimal("1.00"),
                    daily_change_percent=Decimal("1.01"),
                    previous_close=Decimal("9.00"),
                )
            ],
            cash=[
                SimpleNamespace(
                    currency="CAD",
                    amount=Decimal("100.00"),
                )
            ],
        )

        first = service.calculate_current_values(portfolio)
        assert len(market_service.calls) == 2

        second = service.calculate_current_values(portfolio)
        assert len(market_service.calls) == 2
        assert first[2] == second[2]
    finally:
        session.close()
