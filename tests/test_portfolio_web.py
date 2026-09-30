"""Tests for the Sprint 4.4 responsive Portfolio page."""
from datetime import date, datetime
from decimal import Decimal
import sys
import types

from fastapi.testclient import TestClient

from src.api.main import app
from src.models.portfolio_snapshot import PortfolioSnapshot


client = TestClient(app)


def test_portfolio_page_renders_summary(monkeypatch):
    class FakeAccount:
        id = 1
        account_id = 1
        name = "BMO RRSP"
        brokerage_name = "BMO"
        account_number = "1234"
        account_type = "RRSP"
        include_in_portfolio = True
        current_value = Decimal("100000.00")
        holdings_count = 3

    class FakeAccountService:
        def __init__(self, session):
            pass

        def get_summaries(self):
            return [FakeAccount()]

    class FakeSession:
        def scalar(self, statement):
            return PortfolioSnapshot(
                account_id=None,
                snapshot_date=date.today(),
                total_value=Decimal("100000.00"),
                daily_change=Decimal("-1000.00"),
                daily_change_percent=Decimal("-0.99"),
                tsx_daily_change_percent=Decimal("-1.61"),
                valuation_updated_at=datetime(2026, 9, 23, 16, 20),
            )

        def execute(self, statement):
            class Result:
                def scalars(self):
                    return self

                def all(self):
                    return []
            return Result()

        def close(self):
            pass

    monkeypatch.setattr("src.api.main.AccountService", FakeAccountService)
    monkeypatch.setattr("src.api.main.get_session", lambda: FakeSession())

    response = client.get("/portfolio")
    assert response.status_code == 200
    assert "Portfolio" in response.text
    assert "$100,000.00" in response.text
    assert "-1.61%" in response.text
    assert "Brokerage Summary" in response.text



def test_portfolio_page_has_update_controls():
    response = client.get("/portfolio")
    assert response.status_code == 200
    assert 'action="/portfolio/update"' in response.text
    assert 'Update Portfolio' in response.text
    assert 'action="/portfolio/update-tsx"' in response.text
    assert 'Update TSX' in response.text


def test_portfolio_update_calls_valuation_service(monkeypatch):
    calls = {}

    class FakeValuationService:
        def __init__(self, session):
            calls["session"] = session

        def update_all_accounts(self):
            calls["updated"] = True
            return Decimal("123456.78")

    class FakeSession:
        def close(self):
            pass

    monkeypatch.setitem(sys.modules, "yfinance", types.ModuleType("yfinance"))
    monkeypatch.setattr("src.services.portfolio_valuation_service.PortfolioValuationService", FakeValuationService)
    monkeypatch.setattr("src.api.main._portfolio_page_context", lambda session: {
        "accounts": [], "brokerages": [], "total_value": Decimal("123456.78"),
        "daily_change": Decimal("0"), "daily_percent": Decimal("0"),
        "tsx": Decimal("0"), "updated_at": None, "valuation_date": date.today(),
    })
    monkeypatch.setattr("src.api.main.get_session", lambda: FakeSession())
    response = client.post("/portfolio/update")
    assert response.status_code == 200
    assert calls["updated"] is True
    assert "Portfolio updated: $123,456.78" in response.text


def test_portfolio_update_tsx_calls_market_price_service(monkeypatch):
    class FakePrice:
        change_percent = Decimal("-1.61")

    class FakeMarketPriceService:
        def get_price(self, symbol):
            assert symbol == "^GSPTSE"
            return FakePrice()

    class FakeSession:
        def close(self):
            pass

    monkeypatch.setitem(sys.modules, "yfinance", types.ModuleType("yfinance"))
    monkeypatch.setattr("src.services.market_price_service.MarketPriceService", FakeMarketPriceService)
    monkeypatch.setattr("src.api.main._portfolio_page_context", lambda session: {
        "accounts": [], "brokerages": [], "total_value": Decimal("0"),
        "daily_change": Decimal("0"), "daily_percent": Decimal("0"),
        "tsx": Decimal("0"), "updated_at": None, "valuation_date": date.today(),
    })
    monkeypatch.setattr("src.api.main.get_session", lambda: FakeSession())
    response = client.post("/portfolio/update-tsx")
    assert response.status_code == 200
    assert "TSX updated: -1.61%" in response.text


def test_portfolio_page_has_visible_progress_indicator_and_horizontal_actions():
    response = client.get("/portfolio")
    assert response.status_code == 200
    assert 'id="update-progress"' in response.text
    assert 'class="progress-track"' in response.text
    assert 'event.preventDefault()' in response.text
    assert '/portfolio/update?async_update=true' in response.text
    assert '/portfolio/update-status' in response.text
    assert 'class="portfolio-actions"' in response.text


def test_portfolio_update_status_reports_symbol_and_percent(monkeypatch):
    monkeypatch.setattr(
        "src.api.main._get_portfolio_update_state",
        lambda: {
            "running": True,
            "count": 7,
            "total": 20,
            "symbol": "AAPL",
            "percent": 35,
            "message": "Updating Portfolio: 35% — 7 / 20 — AAPL",
            "error": False,
        },
    )

    response = client.get("/portfolio/update-status")

    assert response.status_code == 200
    assert response.json()["symbol"] == "AAPL"
    assert response.json()["percent"] == 35
    assert response.json()["count"] == 7
    assert response.json()["total"] == 20
