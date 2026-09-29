"""Tests for the Sprint 4.4 responsive Portfolio page."""
from datetime import date, datetime
from decimal import Decimal

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

