"""
Tests for Yahoo Finance symbol conversion and fallback behavior.
"""

from decimal import Decimal

import pandas as pd
import pytest

from src.services.market_price_service import MarketPriceService


@pytest.mark.parametrize(
    ("brokerage_symbol", "expected_yahoo_symbol"),
    [
        ("BPO.PR.N:CA", "BPO-PN.TO"),
        ("BPO.PR.A:CA", "BPO-PA.TO"),
        ("BCE.PR.M:CA", "BCE-PM.TO"),
        ("BPO.PR.E:CA", "BPO-PE.TO"),
        ("BPO.PR.P:CA", "BPO-PP.TO"),
    ],
)
def test_convert_canadian_preferred_share(
    brokerage_symbol,
    expected_yahoo_symbol,
):
    """Canadian preferred-share symbols convert algorithmically."""
    assert (
        MarketPriceService._convert_preferred_share_symbol(
            brokerage_symbol
        )
        == expected_yahoo_symbol
    )


def test_convert_preferred_share_returns_none_for_non_preferred_symbol():
    """Non-preferred-share symbols are not converted by the helper."""
    assert (
        MarketPriceService._convert_preferred_share_symbol("BAM:CA")
        is None
    )
    assert (
        MarketPriceService._convert_preferred_share_symbol("AAPL:US")
        is None
    )


def test_yahoo_symbol_candidates_include_preferred_share_fallback():
    """Preferred-share conversion is included after normal conversion."""
    candidates = MarketPriceService._yahoo_symbol_candidates(
        "BPO.PR.N:CA"
    )

    assert candidates == [
        "BPO-PR-N.TO",
        "BPO-PN.TO",
    ]


def test_get_price_retries_preferred_share_candidate(monkeypatch):
    """A failed normal Yahoo symbol is followed by the preferred symbol."""
    service = MarketPriceService()

    calls = []

    class FakeTicker:
        def history(self, **kwargs):
            return pd.DataFrame()

    def fake_ticker(symbol):
        calls.append(symbol)

        if symbol == "BPO-PR-N.TO":
            raise ValueError("symbol not found")

        return FakeTicker()

    monkeypatch.setattr(
        "src.services.market_price_service.yf.Ticker",
        fake_ticker,
    )
    monkeypatch.setattr(
        MarketPriceService,
        "_daily_rows",
        staticmethod(lambda history: []),
    )
    monkeypatch.setattr(
        MarketPriceService,
        "_previous_close",
        staticmethod(lambda rows, today: Decimal("90")),
    )
    monkeypatch.setattr(
        MarketPriceService,
        "_close_for_date",
        staticmethod(lambda rows, today: Decimal("100")),
    )
    monkeypatch.setattr(
        MarketPriceService,
        "_today_regular_session_price",
        staticmethod(lambda history, today: None),
    )

    result = service.get_price("BPO.PR.N:CA")

    assert calls == [
        "BPO-PR-N.TO",
        "BPO-PN.TO",
    ]
    assert result.price == Decimal("100")
    assert result.previous_close == Decimal("90")
    assert result.change == Decimal("10")
    assert result.is_current is True


def test_get_price_returns_unavailable_when_all_yahoo_candidates_fail(
    monkeypatch,
):
    """Yahoo-unavailable securities still return the fallback marker."""
    service = MarketPriceService()

    calls = []

    def fake_ticker(symbol):
        calls.append(symbol)
        raise ValueError("symbol not found")

    monkeypatch.setattr(
        "src.services.market_price_service.yf.Ticker",
        fake_ticker,
    )

    result = service.get_price("BPO.PR.N:CA")

    assert calls == [
        "BPO-PR-N.TO",
        "BPO-PN.TO",
    ]
    assert result.price == Decimal("0")
    assert result.previous_close == Decimal("0")
    assert result.change == Decimal("0")
    assert result.change_percent == Decimal("0")
    assert result.is_current is False
