"""Tests for the Financial Model web API."""

from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.main import app, get_db
from src.services.account_service import AccountSummary
from src.services.portfolio_service import (
    AccountPortfolio,
    PortfolioCash,
    PortfolioHolding,
)
from src.services.portfolio_history_service import PortfolioHistoryPoint
from src.services.account_comparison_history_service import AccountHistoryPoint


class FakeSession:
    """Minimal session object used by mocked API service tests."""

    def close(self) -> None:
        pass


fake_session = FakeSession()


def override_get_db():
    yield fake_session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def teardown_module() -> None:
    app.dependency_overrides.clear()


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_api_endpoint_returns_not_found() -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404


def test_accounts_endpoint_uses_account_service(monkeypatch) -> None:
    summary = AccountSummary(
        account_id=7,
        brokerage_name="BMO",
        account_number="123",
        name="Main",
        account_type="RRSP",
        include_in_portfolio=True,
        current_value=Decimal("123456.78"),
        cash_by_currency={"CAD": Decimal("100.25")},
        holdings_count=3,
        last_import=datetime(2026, 9, 20, 12, 0),
    )

    class FakeAccountService:
        def __init__(self, session):
            assert session is fake_session

        def get_summaries(self):
            return [summary]

    monkeypatch.setattr("src.api.main.AccountService", FakeAccountService)

    response = client.get("/api/accounts")
    assert response.status_code == 200
    assert response.json() == [
        {
            "account_id": 7,
            "brokerage_name": "BMO",
            "account_number": "123",
            "name": "Main",
            "account_type": "RRSP",
            "include_in_portfolio": True,
            "current_value": "123456.78",
            "cash_by_currency": {"CAD": "100.25"},
            "holdings_count": 3,
            "last_import": "2026-09-20T12:00:00",
        }
    ]


def test_portfolio_endpoint_returns_decimal_values_as_strings(monkeypatch) -> None:
    holding = PortfolioHolding(
        snapshot_id=9,
        symbol="AAPL",
        company_name="Apple Inc.",
        quantity=Decimal("10"),
        price=Decimal("250.123456"),
        market_value=Decimal("2501.23456"),
        average_cost=Decimal("200.10"),
        unrealized_gain=Decimal("500.23456"),
        unrealized_gain_percent=Decimal("25.00"),
        daily_change=Decimal("12.34"),
        daily_change_percent=Decimal("0.49"),
        previous_close=Decimal("249.00"),
        current_price=Decimal("250.123456"),
        current_market_value=Decimal("2501.23456"),
        current_previous_close=Decimal("249.00"),
        current_daily_change=Decimal("12.34"),
        current_daily_change_percent=Decimal("0.49"),
        currency="USD",
    )
    portfolio = AccountPortfolio(
        account_id=7,
        snapshot_date=datetime(2026, 9, 20, 12, 0),
        holdings=[holding],
        cash=[PortfolioCash(currency="CAD", amount=Decimal("100.25"))],
    )

    class FakePortfolioService:
        def __init__(self, session):
            assert session is fake_session

        def get_latest_portfolio(self, account_id):
            assert account_id == 7
            return portfolio

    monkeypatch.setattr("src.api.main.PortfolioService", FakePortfolioService)

    response = client.get("/api/portfolio/7")
    assert response.status_code == 200
    body = response.json()
    assert body["snapshot_date"] == "2026-09-20T12:00:00"
    assert body["holdings"][0]["price"] == "250.123456"
    assert body["holdings"][0]["market_value"] == "2501.23456"
    assert body["cash"][0]["amount"] == "100.25"


def test_portfolio_endpoint_returns_404_when_no_import(monkeypatch) -> None:
    class FakePortfolioService:
        def __init__(self, session):
            pass

        def get_latest_portfolio(self, account_id):
            return None

    monkeypatch.setattr("src.api.main.PortfolioService", FakePortfolioService)

    response = client.get("/api/portfolio/999")
    assert response.status_code == 404


def test_holdings_endpoint_can_filter_to_account(monkeypatch) -> None:
    portfolio = AccountPortfolio(
        account_id=7,
        snapshot_date=datetime(2026, 9, 20, 12, 0),
        holdings=[],
        cash=[],
    )

    class FakePortfolioService:
        def __init__(self, session):
            pass

        def get_latest_portfolio(self, account_id):
            assert account_id == 7
            return portfolio

    monkeypatch.setattr("src.api.main.PortfolioService", FakePortfolioService)

    response = client.get("/api/holdings?account_id=7")
    assert response.status_code == 200
    assert response.json()[0]["account_id"] == 7


def test_portfolio_history_endpoint_uses_existing_service(monkeypatch) -> None:
    class FakeAccountService:
        def __init__(self, session):
            pass

        def get_all(self):
            return []

    class FakeHistoryService:
        def __init__(self, session):
            pass

        def get_aggregated_history(self, start_date, end_date, account_ids):
            assert start_date == date(2026, 1, 1)
            assert end_date == date(2026, 9, 20)
            assert account_ids == [7, 8]
            return [
                PortfolioHistoryPoint(
                    snapshot_date=date(2026, 9, 20),
                    total_value=Decimal("1234.56"),
                )
            ]

    monkeypatch.setattr("src.api.main.AccountService", FakeAccountService)
    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService",
        FakeHistoryService,
    )

    response = client.get(
        "/api/portfolio/history"
        "?start_date=2026-01-01"
        "&end_date=2026-09-20"
        "&account_ids=7&account_ids=8"
    )
    assert response.status_code == 200
    assert response.json() == [
        {"snapshot_date": "2026-09-20", "total_value": "1234.56"}
    ]


def test_account_history_endpoint_uses_existing_service(monkeypatch) -> None:
    class FakeAccountService:
        def __init__(self, session):
            pass

        def get(self, account_id):
            return object()

    class FakeHistoryService:
        def __init__(self, session):
            pass

        def get_histories(self, account_ids, start_date, end_date):
            assert account_ids == [7]
            return {
                7: [
                    AccountHistoryPoint(
                        account_id=7,
                        snapshot_date=date(2026, 9, 20),
                        total_value=Decimal("987.65"),
                    )
                ]
            }

    monkeypatch.setattr("src.api.main.AccountService", FakeAccountService)
    monkeypatch.setattr(
        "src.api.main.AccountComparisonHistoryService",
        FakeHistoryService,
    )

    response = client.get(
        "/api/accounts/7/history"
        "?start_date=2026-01-01&end_date=2026-09-20"
    )
    assert response.status_code == 200
    assert response.json() == [
        {
            "account_id": 7,
            "snapshot_date": "2026-09-20",
            "total_value": "987.65",
        }
    ]


def test_history_rejects_reversed_dates_before_account_lookup(monkeypatch) -> None:
    class UnexpectedAccountService:
        def __init__(self, session):
            raise AssertionError("Account lookup should not occur for invalid dates")

    monkeypatch.setattr(
        "src.api.main.AccountService",
        UnexpectedAccountService,
    )

    response = client.get(
        "/api/accounts/7/history"
        "?start_date=2026-09-21&end_date=2026-09-20"
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "start_date must be on or before end_date."
    }
