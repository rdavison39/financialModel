"""Tests for Portfolio tab TSX-only update behavior."""

from decimal import Decimal

from src.gui import portfolio_tab


class FakeMarketPrice:
    change_percent = Decimal("-1.607734120880315481149208724")


class FakeMarketPriceService:
    def get_price(self, symbol):
        assert symbol == "^GSPTSE"
        return FakeMarketPrice()


def test_tsx_worker_does_not_require_a_portfolio_valuation(monkeypatch):
    monkeypatch.setattr(
        portfolio_tab,
        "MarketPriceService",
        FakeMarketPriceService,
    )

    class Queue: 
        def __init__(self):
            self.messages = []
        def put(self, message):
            self.messages.append(message)

    # Bypass Tk construction; exercise only the worker logic.
    tab = portfolio_tab.PortfolioTab.__new__(portfolio_tab.PortfolioTab)
    tab._update_queue = Queue()

    tab._run_tsx_update_worker()

    assert tab._update_queue.messages == [
        ("tsx_complete", FakeMarketPrice.change_percent)
    ]
