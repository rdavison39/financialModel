from datetime import date
from decimal import Decimal

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.services.market_price_service import MarketPrice
from src.services.portfolio_valuation_service import PortfolioValuationService


class FakeMarketPriceService:
    def get_price(self, symbol):
        assert symbol == "^GSPTSE"
        return MarketPrice(
            price=Decimal("35751.43"),
            previous_close=Decimal("36335.61"),
            change=Decimal("-584.18"),
            change_percent=(
                Decimal("-584.18")
                / Decimal("36335.61")
                * Decimal("100")
            ),
            is_current=True,
        )


def test_update_tsx_only_changes_tsx_and_nothing_else(session):
    brokerage = Brokerage(name="BMO")
    session.add(brokerage)
    session.flush()

    account = Account(
        brokerage_id=brokerage.id,
        account_number="123",
        name="Test",
        include_in_portfolio=True,
    )
    session.add(account)
    session.flush()

    today = date.today()
    account_snapshot = PortfolioSnapshot(
        account_id=account.id,
        snapshot_date=today,
        total_value=Decimal("100000.00"),
        daily_change=Decimal("-500.00"),
        daily_change_percent=Decimal("-0.50"),
        tsx_daily_change_percent=Decimal("-0.72"),
        usd_to_cad=Decimal("1.38000000"),
    )
    consolidated_snapshot = PortfolioSnapshot(
        account_id=None,
        snapshot_date=today,
        total_value=Decimal("100000.00"),
        daily_change=Decimal("-500.00"),
        daily_change_percent=Decimal("-0.50"),
        tsx_daily_change_percent=Decimal("-0.72"),
        usd_to_cad=Decimal("1.38000000"),
    )
    session.add_all([account_snapshot, consolidated_snapshot])
    session.commit()

    service = PortfolioValuationService(
        session,
        market_price_service=FakeMarketPriceService(),
    )

    result = service.update_tsx_only()

    assert result == (
        Decimal("-584.18") / Decimal("36335.61") * Decimal("100")
    )

    session.refresh(account_snapshot)
    session.refresh(consolidated_snapshot)

    expected_stored_value = result.quantize(Decimal("0.000001"))

    assert account_snapshot.tsx_daily_change_percent == expected_stored_value
    assert consolidated_snapshot.tsx_daily_change_percent == expected_stored_value
    assert consolidated_snapshot.total_value == Decimal("100000.00")
    assert consolidated_snapshot.daily_change == Decimal("-500.00")
    assert consolidated_snapshot.daily_change_percent == Decimal("-0.50")
    assert consolidated_snapshot.usd_to_cad == Decimal("1.38000000")
