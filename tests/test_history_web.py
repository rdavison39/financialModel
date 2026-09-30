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
    PortfolioHistoryService,
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


def test_portfolio_benchmark_is_aligned_to_portfolio_dates(monkeypatch):
    monkeypatch.setattr(
        "src.api.main.AccountComparisonHistoryService.get_accounts",
        lambda self: _accounts(),
    )
    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_aggregated_history",
        lambda *args: [
            PortfolioHistoryPoint(date(2026, 9, 22), Decimal("100"), Decimal("1"), Decimal("1.0")),
            PortfolioHistoryPoint(date(2026, 9, 23), Decimal("99"), Decimal("-1"), Decimal("-1.0")),
        ],
    )
    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_benchmark_history",
        lambda *args: [
            BenchmarkHistoryPoint(date(2026, 9, 21), Decimal("36000")),
            BenchmarkHistoryPoint(date(2026, 9, 22), Decimal("36335.61")),
            BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("35751.43")),
            BenchmarkHistoryPoint(date(2026, 9, 24), Decimal("35900")),
        ],
    )

    response = TestClient(app).get(
        "/portfolio/history?view=%25%20Day's%20Gain/Loss"
        "&benchmark=TSX%20Composite&start_date=2026-09-22&end_date=2026-09-23"
    )

    assert response.status_code == 200
    assert '2026-09-22' in response.text
    assert '2026-09-23' in response.text
    # The benchmark chart data should not include unrelated trading dates.
    assert '2026-09-21' not in response.text
    assert '2026-09-24' not in response.text


def test_history_template_has_limited_date_axis_labels():
    template = __import__("pathlib").Path("src/templates/history.html").read_text()
    assert "const labelCount = Math.min(6, axisDates.length);" in template
    assert "axisDates[index]" in template


def test_portfolio_history_can_show_selected_brokerage_lines(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "src.api.main.AccountComparisonHistoryService.get_accounts",
        lambda self: _accounts(),
    )

    def fake_history(self, start, end, account_ids):
        calls.append(list(account_ids))
        if account_ids == [1]:
            return [
                PortfolioHistoryPoint(date(2026, 9, 22), Decimal("60"), Decimal("0"), Decimal("0")),
                PortfolioHistoryPoint(date(2026, 9, 23), Decimal("61"), Decimal("1"), Decimal("1.67")),
            ]
        if account_ids == [2]:
            return [
                PortfolioHistoryPoint(date(2026, 9, 22), Decimal("40"), Decimal("0"), Decimal("0")),
                PortfolioHistoryPoint(date(2026, 9, 23), Decimal("39"), Decimal("-1"), Decimal("-2.50")),
            ]
        return [
            PortfolioHistoryPoint(date(2026, 9, 22), Decimal("100"), Decimal("0"), Decimal("0")),
            PortfolioHistoryPoint(date(2026, 9, 23), Decimal("100"), Decimal("0"), Decimal("0")),
        ]

    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_aggregated_history",
        fake_history,
    )
    monkeypatch.setattr(
        "src.api.main.PortfolioHistoryService.get_benchmark_history",
        lambda *args: [
            BenchmarkHistoryPoint(date(2026, 9, 22), Decimal("100")),
            BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("101")),
        ],
    )

    response = TestClient(app).get(
        "/portfolio/history?view=%25%20Day's%20Gain/Loss"
        "&brokerage_lines=BMO&brokerage_lines=NB"
    )

    assert response.status_code == 200
    assert 'name="brokerage_lines" value="BMO" checked' in response.text
    assert 'name="brokerage_lines" value="NB" checked' in response.text
    assert 'BMO' in response.text
    assert 'NB' in response.text
    assert [1, 2] in calls
    assert [1] in calls
    assert [2] in calls


def test_portfolio_history_brokerage_lines_are_unchecked_by_default(monkeypatch):
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

    response = TestClient(app).get("/portfolio/history?view=%25%20Growth%20Since%20Start")

    assert response.status_code == 200
    assert 'name="brokerage_lines" value="BMO" checked' not in response.text
    assert 'name="brokerage_lines" value="NB" checked' not in response.text


def test_portfolio_history_uses_shared_metric_calculation(monkeypatch):
    calls = []
    monkeypatch.setattr("src.api.main.AccountComparisonHistoryService.get_accounts", lambda self: _accounts())
    monkeypatch.setattr("src.api.main.PortfolioHistoryService.get_aggregated_history", lambda self, start, end, account_ids: [
        PortfolioHistoryPoint(date(2026, 9, 22), Decimal("100"), Decimal("1"), Decimal("1")),
        PortfolioHistoryPoint(date(2026, 9, 23), Decimal("110"), Decimal("10"), Decimal("10")),
    ])
    monkeypatch.setattr("src.api.main.PortfolioHistoryService.get_benchmark_history", lambda *args: [
        BenchmarkHistoryPoint(date(2026, 9, 22), Decimal("100")),
        BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("101")),
    ])
    original = PortfolioHistoryService.calculate_metric_values
    def wrapped(cls, history, view):
        calls.append(view)
        return original(history, view)
    monkeypatch.setattr(PortfolioHistoryService, "calculate_metric_values", classmethod(wrapped))
    response = TestClient(app).get("/portfolio/history?view=%25%20Growth%20Since%20Start&start_date=2026-09-22&end_date=2026-09-23")
    assert response.status_code == 200
    assert "% Growth Since Start" in calls


def test_portfolio_history_uses_shared_benchmark_calculation(monkeypatch):
    calls = []
    monkeypatch.setattr("src.api.main.AccountComparisonHistoryService.get_accounts", lambda self: _accounts())
    monkeypatch.setattr("src.api.main.PortfolioHistoryService.get_aggregated_history", lambda self, start, end, account_ids: [
        PortfolioHistoryPoint(date(2026, 9, 22), Decimal("100")),
        PortfolioHistoryPoint(date(2026, 9, 23), Decimal("110")),
    ])
    monkeypatch.setattr("src.api.main.PortfolioHistoryService.get_benchmark_history", lambda *args: [
        BenchmarkHistoryPoint(date(2026, 9, 22), Decimal("100")),
        BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("99")),
    ])
    original = PortfolioHistoryService.calculate_benchmark_growth
    def wrapped(cls, history):
        calls.append("growth")
        return original(history)
    monkeypatch.setattr(PortfolioHistoryService, "calculate_benchmark_growth", classmethod(wrapped))
    response = TestClient(app).get("/portfolio/history?view=%25%20Growth%20Since%20Start&start_date=2026-09-22&end_date=2026-09-23")
    assert response.status_code == 200
    assert "growth" in calls
