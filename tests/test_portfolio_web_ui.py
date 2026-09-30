"""Tests for the Portfolio web action/status UI."""
import sys
import types
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def _portfolio_context() -> dict:
    """Return the minimal Portfolio page context used by the UI tests."""
    return {
        "accounts": [],
        "brokerages": [],
        "total_value": Decimal("123456.78"),
        "daily_change": Decimal("100.00"),
        "daily_percent": Decimal("0.08"),
        "tsx": Decimal("-1.61"),
        "updated_at": None,
        "valuation_date": None,
    }


def test_portfolio_page_contains_side_by_side_update_actions(monkeypatch):
    """The Portfolio page exposes both update actions in one action group."""
    monkeypatch.setattr(
        "src.api.main._portfolio_page_context",
        lambda session: _portfolio_context(),
    )

    response = client.get("/portfolio")

    assert response.status_code == 200
    assert 'action="/portfolio/update"' in response.text
    assert 'action="/portfolio/update-tsx"' in response.text
    assert 'class="portfolio-actions"' in response.text
    assert 'data-update-form' in response.text


def test_portfolio_update_displays_status_message(monkeypatch):
    """A successful Portfolio update renders a visible status message."""
    monkeypatch.setitem(sys.modules, "yfinance", types.ModuleType("yfinance"))
    class FakeValuationService:
        def __init__(self, session):
            pass

        def update_all_accounts(self):
            return Decimal("123456.78")

    monkeypatch.setattr(
        "src.services.portfolio_valuation_service.PortfolioValuationService",
        FakeValuationService,
    )
    monkeypatch.setattr(
        "src.api.main._portfolio_page_context",
        lambda session: _portfolio_context(),
    )

    response = client.post("/portfolio/update")

    assert response.status_code == 200
    assert 'class="status-message positive"' in response.text
    assert "Portfolio updated: $123,456.78" in response.text
