from datetime import date, timedelta
from decimal import Decimal

import pandas as pd

from src.services.market_price_service import MarketPriceService


def test_preferred_share_conversion_is_algorithmic():
    service = MarketPriceService()

    assert service._convert_preferred_share_symbol(
        "BPO.PR.A:CA"
    ) == "BPO-PA.TO"

    assert service._convert_preferred_share_symbol(
        "BCE.PR.M:CA"
    ) == "BCE-PM.TO"


def test_yahoo_candidates_try_algorithmic_preferred_conversion():
    candidates = MarketPriceService._yahoo_symbol_candidates(
        "BPO.PR.A:CA"
    )

    assert candidates[0] == "BPO-PR-A.TO"
    assert "BPO-PA.TO" in candidates


def test_preferred_share_can_use_daily_data_when_intraday_fails(
    monkeypatch,
):
    today = date.today()

    daily_history = pd.DataFrame(
        {"Close": [22.80, 22.93]},
        index=pd.to_datetime(
            [
                today - timedelta(days=2),
                today - timedelta(days=1),
            ]
        ),
    )

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, *, period, interval):
            if self.symbol == "BPO-PR-A.TO":
                raise RuntimeError("Normal conversion is not a Yahoo symbol")

            if interval == "1m":
                raise RuntimeError("No intraday data")

            return daily_history

    monkeypatch.setattr(
        "src.services.market_price_service.yf.Ticker",
        lambda symbol: FakeTicker(symbol),
    )

    service = MarketPriceService()
    result = service.get_price("BPO.PR.A:CA")

    assert result.is_current is True
    assert result.price == Decimal("22.93")
    assert result.previous_close == Decimal("22.93")
