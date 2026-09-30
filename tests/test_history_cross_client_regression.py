"""Cross-client regression tests for shared Portfolio History calculations."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.api.main import _benchmark_series, _portfolio_history_series
from src.gui.graphs_tab import GraphsTab
from src.services.portfolio_history_service import (
    BenchmarkHistoryPoint,
    PortfolioHistoryPoint,
    PortfolioHistoryService,
)


def make_tab(view: str):
    tab = GraphsTab.__new__(GraphsTab)
    tab.view_mode = SimpleNamespace(get=lambda: view)
    tab._last_benchmark = []
    tab._benchmark_previous_value = None
    return tab


def make_history_points():
    return [
        PortfolioHistoryPoint(
            date(2026, 9, 21),
            Decimal("100000"),
            Decimal("500"),
            Decimal("0.50"),
        ),
        # Weekend observation.  Performance views must omit it.
        PortfolioHistoryPoint(
            date(2026, 9, 20),
            Decimal("100500"),
            Decimal("500"),
            Decimal("0.50"),
        ),
        PortfolioHistoryPoint(
            date(2026, 9, 22),
            Decimal("101500"),
            Decimal("1000"),
            Decimal("0.995024875621890547"),
        ),
        PortfolioHistoryPoint(
            date(2026, 9, 23),
            Decimal("99900"),
            Decimal("-1600"),
            Decimal("-1.576354679802955665"),
        ),
    ]


TRADING_DATES = {
    date(2026, 9, 21),
    date(2026, 9, 22),
    date(2026, 9, 23),
}


def test_desktop_and_web_portfolio_views_produce_identical_values():
    points = make_history_points()

    for view in (
        "Portfolio Value",
        "% Growth Since Start",
        "Day's Gain/Loss",
        "% Day's Gain/Loss",
    ):
        desktop_points = (
            points
            if view == "Portfolio Value"
            else [point for point in points if point.snapshot_date in TRADING_DATES]
        )
        desktop_values = make_tab(view)._transform_history(desktop_points)

        web_series = _portfolio_history_series(points, view, TRADING_DATES)
        web_values = [Decimal(item["value"]) for item in web_series]
        web_dates = [date.fromisoformat(item["date"]) for item in web_series]

        assert web_dates == [point.snapshot_date for point in desktop_points]
        assert web_values == desktop_values


def test_desktop_and_web_growth_benchmark_are_identical():
    portfolio_history = [
        PortfolioHistoryPoint(date(2026, 9, 22), Decimal("100000")),
        PortfolioHistoryPoint(date(2026, 9, 23), Decimal("99000")),
    ]
    benchmark_history = [
        BenchmarkHistoryPoint(date(2026, 9, 22), Decimal("36335.61")),
        BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("35751.43")),
    ]

    service = PortfolioHistoryService.__new__(PortfolioHistoryService)
    service.get_benchmark_history = lambda symbol, start, end: [
        BenchmarkHistoryPoint(date(2026, 9, 21), Decimal("36009.40")),
        *benchmark_history,
    ]

    web_series = _benchmark_series(
        service,
        "TSX Composite",
        "",
        "% Growth Since Start",
        portfolio_history,
    )

    desktop_tab = make_tab("% Growth Since Start")
    desktop_tab._last_benchmark = benchmark_history
    desktop_values = desktop_tab._benchmark_growth_values()

    assert [date.fromisoformat(item["date"]) for item in web_series] == [
        point.snapshot_date for point in benchmark_history
    ]
    assert [Decimal(item["value"]) for item in web_series] == desktop_values


def test_desktop_and_web_tsx_daily_change_use_same_previous_close():
    portfolio_history = [
        PortfolioHistoryPoint(date(2026, 9, 22), Decimal("101500")),
        PortfolioHistoryPoint(date(2026, 9, 23), Decimal("99900")),
    ]
    benchmark_history = [
        BenchmarkHistoryPoint(date(2026, 9, 22), Decimal("36335.61")),
        BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("35751.43")),
    ]
    raw_benchmark_history = [
        BenchmarkHistoryPoint(date(2026, 9, 21), Decimal("36009.40")),
        *benchmark_history,
    ]

    service = PortfolioHistoryService.__new__(PortfolioHistoryService)
    service.get_benchmark_history = lambda symbol, start, end: raw_benchmark_history

    web_series = _benchmark_series(
        service,
        "TSX Composite",
        "",
        "% Day's Gain/Loss",
        portfolio_history,
    )

    desktop_tab = make_tab("% Day's Gain/Loss")
    desktop_tab._last_benchmark = benchmark_history
    desktop_tab._benchmark_previous_value = Decimal("36009.40")
    desktop_values = desktop_tab._benchmark_daily_change_percent_values()

    web_values = [Decimal(item["value"]) for item in web_series]

    assert web_values == desktop_values
    assert round(float(web_values[-1]), 2) == -1.61
