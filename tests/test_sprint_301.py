"""
Tests for Sprint 3.0.1 portfolio valuation caching.
"""

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine, select
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


def test_update_all_accounts_excludes_accounts_from_consolidated_totals():
    """Only included accounts contribute to consolidated valuation data."""
    session = make_session()

    class FakeMarketPriceService:
        def get_price(self, symbol):
            if symbol == "CAD=X":
                return MarketPrice(
                    price=Decimal("1.00"),
                    previous_close=Decimal("1.00"),
                    change=Decimal("0"),
                    change_percent=Decimal("0"),
                    is_current=True,
                )
            if symbol == "^GSPTSE":
                return MarketPrice(
                    price=Decimal("25000"),
                    previous_close=Decimal("24900"),
                    change=Decimal("100"),
                    change_percent=Decimal("0.4016"),
                    is_current=True,
                )
            return MarketPrice(
                price=Decimal("10.00"),
                previous_close=Decimal("9.00"),
                change=Decimal("1.00"),
                change_percent=Decimal("11.1111"),
                is_current=True,
            )

    brokerage = Brokerage(name="Test Brokerage")
    session.add(brokerage)
    session.flush()

    included = Account(
        brokerage_id=brokerage.id,
        account_number="100",
        name="Included",
        include_in_portfolio=True,
    )
    excluded = Account(
        brokerage_id=brokerage.id,
        account_number="200",
        name="Excluded",
        include_in_portfolio=False,
    )
    session.add_all([included, excluded])
    session.commit()

    included_portfolio = SimpleNamespace(
        holdings=[
            SimpleNamespace(
                symbol="AAA:CA", company_name="AAA", quantity=Decimal("10"),
                price=Decimal("9"), market_value=Decimal("90"),
                currency="CAD", average_cost=Decimal("8"),
                unrealized_gain=Decimal("10"),
                unrealized_gain_percent=Decimal("12.5"),
                daily_change=Decimal("10"),
                daily_change_percent=Decimal("11.1111"),
                previous_close=Decimal("9"),
            )
        ],
        cash=[],
    )
    excluded_portfolio = SimpleNamespace(
        holdings=[
            SimpleNamespace(
                symbol="BBB:CA", company_name="BBB", quantity=Decimal("20"),
                price=Decimal("9"), market_value=Decimal("180"),
                currency="CAD", average_cost=Decimal("8"),
                unrealized_gain=Decimal("20"),
                unrealized_gain_percent=Decimal("12.5"),
                daily_change=Decimal("20"),
                daily_change_percent=Decimal("11.1111"),
                previous_close=Decimal("9"),
            )
        ],
        cash=[],
    )

    service = PortfolioValuationService(
        session,
        market_price_service=FakeMarketPriceService(),
    )

    portfolios = {
        included.id: included_portfolio,
        excluded.id: excluded_portfolio,
    }
    service.portfolio_service.get_latest_portfolio = (
        lambda account_id: portfolios[account_id]
    )

    total = service.update_all_accounts()

    assert total == Decimal("100")
    assert service.total_daily_change == Decimal("10")

    consolidated = session.scalar(
        select(PortfolioSnapshot).where(
            PortfolioSnapshot.account_id.is_(None),
            PortfolioSnapshot.snapshot_date == date.today(),
        )
    )

    assert consolidated is not None
    assert consolidated.total_value == Decimal("100")
    assert consolidated.daily_change == Decimal("10")

    account_snapshots = session.scalars(
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.account_id.is_not(None))
        .order_by(PortfolioSnapshot.account_id)
    ).all()

    assert len(account_snapshots) == 2
    assert account_snapshots[0].total_value == Decimal("100")
    assert account_snapshots[1].total_value == Decimal("200")

    assert consolidated.valuation_data is not None
    assert '"AAA:CA"' in consolidated.valuation_data
    assert '"BBB:CA"' not in consolidated.valuation_data
