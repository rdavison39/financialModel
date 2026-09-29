from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from src.api.main import app, get_db
from src.services.account_comparison_history_service import (
    AccountComparison,
    AccountHistoryPoint,
)
from src.services.portfolio_comparison_service import (
    PortfolioComparison,
    PositionComparison,
)
from src.services.portfolio_history_service import (
    BenchmarkHistoryPoint,
    PortfolioHistoryPoint,
)


class DummySession:
    """Session stand-in for web-route tests."""



def _accounts():
    return [
        AccountComparison(1, "BMO", "123", "Main"),
        AccountComparison(2, "NB", "456", "Retirement"),
    ]


def setup_function():
    app.dependency_overrides[get_db] = lambda: DummySession()


def teardown_function():
    app.dependency_overrides.clear()


def test_portfolio_history_defaults_to_one_year_and_all_accounts(monkeypatch):
    calls = {}

    def fake_accounts(self):
        return _accounts()

    def fake_history(self, start, end, account_ids):
        calls["range"] = (start, end)
        calls["accounts"] = account_ids
        return [
            PortfolioHistoryPoint(date(2026, 9, 23), Decimal("100"), Decimal("-2"), Decimal("-1.96")),
        ]

    monkeypatch.setattr(
        "src.api.main.AccountComparisonHistoryService.get_accounts",
        fake_accounts,
    )
    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_aggregated_history",
        fake_history,
    )
    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_benchmark_history",
        lambda *args: [BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("35751.43"))],
    )

    response = TestClient(app).get("/portfolio/history?view=Portfolio%20Value")

    assert response.status_code == 200
    assert "Portfolio History" in response.text
    assert calls["accounts"] == [1, 2]
    assert calls["range"][1] == date.today()


def test_portfolio_history_uses_stable_account_keys(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        "src.api.main.AccountComparisonHistoryService.get_accounts",
        lambda self: _accounts(),
    )

    def fake_history(self, start, end, account_ids):
        calls["accounts"] = account_ids
        return []

    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_aggregated_history",
        fake_history,
    )
    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_benchmark_history",
        lambda *args: [],
    )

    response = TestClient(app).get(
        "/portfolio/history?account_keys=BMO%7C123%7CMain&view=Portfolio%20Value"
    )

    assert response.status_code == 200
    assert calls["accounts"] == [1]


def test_account_history_supports_percentage_view_and_benchmark(monkeypatch):
    monkeypatch.setattr(
        "src.api.main.AccountComparisonHistoryService.get_accounts",
        lambda self: _accounts(),
    )
    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_benchmark_history",
        lambda *args: [
            BenchmarkHistoryPoint(date(2026, 9, 22), Decimal("36335.61")),
            BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("35751.43")),
        ],
    )
    monkeypatch.setattr(
        "src.api.main.AccountComparisonHistoryService.get_histories",
        lambda self, account_ids, start, end: {
            1: [
                AccountHistoryPoint(1, date(2026, 9, 22), Decimal("100"), Decimal("1"), Decimal("1.01")),
                AccountHistoryPoint(1, date(2026, 9, 23), Decimal("99"), Decimal("-1"), Decimal("-1.0")),
            ]
        },
    )

    response = TestClient(app).get(
        "/accounts/history?account_keys=BMO%7C123%7CMain&view=%25%20Day's%20Gain/Loss"
        "&start_date=2026-09-22&end_date=2026-09-23"
    )

    assert response.status_code == 200
    assert "Day&#39;s Gain/Loss" in response.text
    assert "TSX Composite" in response.text
    assert "-1.00%" in response.text


def test_percentage_benchmark_is_disabled_for_value_view(monkeypatch):
    monkeypatch.setattr(
        "src.api.main.AccountComparisonHistoryService.get_accounts",
        lambda self: _accounts(),
    )
    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_aggregated_history",
        lambda *args: [],
    )
    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_benchmark_history",
        lambda *args: [],
    )

    response = TestClient(app).get("/portfolio/history?view=Portfolio%20Value&benchmark=TSX%20Composite")

    assert response.status_code == 200
    assert 'id="benchmark-select" disabled' in response.text


def test_holdings_history_uses_existing_comparison_service(monkeypatch):
    monkeypatch.setattr(
        "src.api.main.AccountComparisonHistoryService.get_accounts",
        lambda self: _accounts(),
    )
    monkeypatch.setattr(
        "src.api.main.PortfolioComparisonService.compare",
        lambda self, first, second, account_id: PortfolioComparison(
            Decimal("100"),
            Decimal("110"),
            Decimal("10"),
            [
                PositionComparison(
                    "ABC", "ABC Corp", Decimal("10"), Decimal("12"), Decimal("2"),
                    Decimal("5"), Decimal("5"), Decimal("50"), Decimal("60"),
                    Decimal("2"), Decimal("3"), "CAD", "Increased",
                )
            ],
        ),
    )

    response = TestClient(app).get(
        "/holdings/history?account_key=BMO%7C123%7CMain&from_date=2026-09-22&to_date=2026-09-23"
    )

    assert response.status_code == 200
    assert "ABC" in response.text
    assert "$+10.00" in response.text
