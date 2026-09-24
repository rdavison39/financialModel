"""Tests for Portfolio History chart view transformations and benchmark rules."""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from src.gui.graphs_tab import GraphsTab
from src.services.portfolio_history_service import (
    BenchmarkHistoryPoint,
    PortfolioHistoryPoint,
)


def make_tab(view: str):
    tab = GraphsTab.__new__(GraphsTab)
    tab.view_mode = SimpleNamespace(get=lambda: view)
    return tab


def make_points():
    return [
        PortfolioHistoryPoint(
            date(2026, 9, 22),
            Decimal("100000"),
            Decimal("1500"),
            Decimal("1.522842639593908629"),
        ),
        PortfolioHistoryPoint(
            date(2026, 9, 23),
            Decimal("98500"),
            Decimal("-1500"),
            Decimal("-1.500750375187593797"),
        ),
    ]


def test_portfolio_history_has_four_view_metrics():
    expected = {
        "Portfolio Value",
        "% Growth Since Start",
        "Day's Gain/Loss",
        "% Day's Gain/Loss",
    }
    source = open("src/gui/graphs_tab.py", encoding="utf-8").read()
    for value in expected:
        assert f'"{value}"' in source

    assert '"Dollar Value"' not in source
    assert '"Growth Since Start (%)"' not in source
    assert '"Day\'s % Gain/Loss"' not in source
    assert '"Daily Change"' not in source
    assert '"% Daily Change"' not in source


def test_portfolio_history_view_transformations():
    points = make_points()

    assert make_tab("Portfolio Value")._transform_history(points) == [
        Decimal("100000"),
        Decimal("98500"),
    ]
    assert make_tab("% Growth Since Start")._transform_history(points) == [
        Decimal("0"),
        Decimal("-1.5"),
    ]
    assert make_tab("Day's Gain/Loss")._transform_history(points) == [
        Decimal("1500"),
        Decimal("-1500"),
    ]
    assert make_tab("% Day's Gain/Loss")._transform_history(points) == [
        Decimal("1.522842639593908629"),
        Decimal("-1.500750375187593797"),
    ]


def test_portfolio_history_benchmark_only_supported_for_percent_views():
    assert make_tab("Portfolio Value")._benchmark_is_supported() is False
    assert make_tab("Day's Gain/Loss")._benchmark_is_supported() is False
    assert make_tab("% Growth Since Start")._benchmark_is_supported() is True
    assert make_tab("% Day's Gain/Loss")._benchmark_is_supported() is True


def test_portfolio_history_benchmark_daily_percentages():
    tab = make_tab("% Day's Gain/Loss")
    tab._last_benchmark = [
        BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("35751.43")),
    ]
    tab._benchmark_previous_value = Decimal("36335.61")

    value = tab._benchmark_daily_change_percent_values()[0]
    expected = (
        Decimal("35751.43") - Decimal("36335.61")
    ) / Decimal("36335.61") * Decimal("100")
    assert value == expected
    assert round(float(value), 2) == -1.61


def test_portfolio_history_benchmark_daily_percentage_uses_previous_trading_close():
    tab = make_tab("% Day's Gain/Loss")
    tab._benchmark_previous_value = Decimal("36335.61")
    tab._last_benchmark = [
        BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("35751.43")),
    ]

    value = tab._benchmark_daily_change_percent_values()[0]
    assert round(float(value), 2) == -1.61


def test_portfolio_history_benchmark_ignores_weekend_observations():
    tab = make_tab("% Day's Gain/Loss")
    tab._benchmark_previous_value = Decimal("35806.65")
    tab._last_benchmark = [
        BenchmarkHistoryPoint(date(2026, 9, 20), Decimal("40000")),
        BenchmarkHistoryPoint(date(2026, 9, 21), Decimal("36009.40")),
        BenchmarkHistoryPoint(date(2026, 9, 22), Decimal("36335.61")),
        BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("35751.43")),
    ]

    values = tab._benchmark_daily_change_percent_values()
    assert len(values) == 3
    assert round(float(values[-1]), 2) == -1.61


def test_portfolio_history_uses_selected_account_aggregation():
    source = open("src/gui/graphs_tab.py", encoding="utf-8").read()
    assert "service.get_aggregated_history(" in source
    assert "account_ids=account_ids" in source


def test_portfolio_history_filters_weekends_and_holidays_from_performance_views():
    points = [
        PortfolioHistoryPoint(date(2026, 9, 18), Decimal("100000")),
        PortfolioHistoryPoint(date(2026, 9, 20), Decimal("100000")),
        PortfolioHistoryPoint(date(2026, 9, 21), Decimal("101000")),
        PortfolioHistoryPoint(date(2026, 12, 25), Decimal("101000")),
    ]

    trading_days = {date(2026, 9, 18), date(2026, 9, 21)}

    filtered = GraphsTab._filter_to_trading_days(points, trading_days)

    assert [point.snapshot_date for point in filtered] == [
        date(2026, 9, 18),
        date(2026, 9, 21),
    ]
