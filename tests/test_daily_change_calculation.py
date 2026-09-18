from decimal import Decimal
from types import SimpleNamespace

from src.services.portfolio_valuation_service import (
    MarketPrice,
    PortfolioValuationService,
)


def holding(**kwargs):
    defaults = {
        "symbol": "AAA:CA",
        "quantity": Decimal("100"),
        "currency": "CAD",
        "daily_change": Decimal("9999"),
        "daily_change_percent": Decimal("999"),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def market_price(price: str, previous_close: str) -> MarketPrice:
    return MarketPrice(
        price=Decimal(price),
        previous_close=Decimal(previous_close),
        change=Decimal(price) - Decimal(previous_close),
        change_percent=Decimal("0"),
        is_current=True,
    )


def test_daily_change_uses_quantity_times_quote_delta_not_imported_value():
    result = PortfolioValuationService._calculate_holding_daily_change(
        holding(),
        market_price("12.50", "12.00"),
        Decimal("1.35"),
    )

    assert result == Decimal("50")


def test_usd_daily_change_is_converted_to_cad():
    result = PortfolioValuationService._calculate_holding_daily_change(
        holding(
            symbol="AAA:US",
            currency="USD",
            quantity=Decimal("200"),
        ),
        market_price("25.25", "25.00"),
        Decimal("1.35"),
    )

    assert result == Decimal("67.5000")


def test_option_daily_change_uses_100_share_contract_multiplier():
    result = PortfolioValuationService._calculate_holding_daily_change(
        holding(
            symbol="CALL AAA 2026-12-18 100",
            quantity=Decimal("3"),
        ),
        market_price("4.20", "3.80"),
        Decimal("1.00"),
    )

    assert result == Decimal("120.00")


def test_daily_change_percent_uses_previous_close_position_value():
    result = PortfolioValuationService._calculate_holding_daily_change_percent(
        holding(quantity=Decimal("100")),
        market_price("12.50", "12.00"),
        Decimal("1.00"),
    )

    assert result == (Decimal("0.50") / Decimal("12.00")) * Decimal("100")
