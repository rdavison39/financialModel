"""Tests for Account History chart view transformations and benchmarks."""

from datetime import date
from decimal import Decimal

from src.gui.account_comparison_tab import AccountComparisonTab
from src.services.account_comparison_history_service import AccountHistoryPoint
from src.services.portfolio_history_service import BenchmarkHistoryPoint


def make_points():
    return [
        AccountHistoryPoint(
            account_id=1,
            snapshot_date=date(2026, 9, 22),
            total_value=Decimal("100000"),
            daily_change=Decimal("1500"),
            daily_change_percent=Decimal("1.522842639593908629"),
        ),
        AccountHistoryPoint(
            account_id=1,
            snapshot_date=date(2026, 9, 23),
            total_value=Decimal("98500"),
            daily_change=Decimal("-1500"),
            daily_change_percent=Decimal("-1.500750375187593797"),
        ),
    ]


def test_account_history_view_transformations():
    points = make_points()

    assert AccountComparisonTab._transform_account_history(
        points, "Portfolio Value"
    ) == [Decimal("100000"), Decimal("98500")]

    assert AccountComparisonTab._transform_account_history(
        points, "% Growth Since Start"
    ) == [Decimal("0"), Decimal("-1.5")]

    assert AccountComparisonTab._transform_account_history(
        points, "Day's Gain/Loss"
    ) == [Decimal("1500"), Decimal("-1500")]

    assert AccountComparisonTab._transform_account_history(
        points, "% Day's Gain/Loss"
    ) == [
        Decimal("1.522842639593908629"),
        Decimal("-1.500750375187593797"),
    ]


def test_account_history_benchmarks_only_apply_to_percentage_views():
    for view in ("Portfolio Value", "Day's Gain/Loss"):
        tab = AccountComparisonTab.__new__(AccountComparisonTab)
        tab.view_var = type("View", (), {"get": lambda self: view})()
        assert tab._benchmark_is_supported() is False

    for view in ("% Growth Since Start", "% Day's Gain/Loss"):
        tab = AccountComparisonTab.__new__(AccountComparisonTab)
        tab.view_var = type("View", (), {"get": lambda self: view})()
        assert tab._benchmark_is_supported() is True


def test_account_history_benchmark_daily_change_uses_previous_close():
    tab = AccountComparisonTab.__new__(AccountComparisonTab)
    tab._benchmark_previous_value = Decimal("36335.61")
    tab._last_benchmark = [
        BenchmarkHistoryPoint(date(2026, 9, 23), Decimal("35751.43")),
    ]

    value = tab._benchmark_daily_change_percent_values()[0]
    assert round(float(value), 2) == -1.61


def test_account_history_benchmark_ignores_weekend_observations():
    tab = AccountComparisonTab.__new__(AccountComparisonTab)
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


def test_account_history_daily_fallback_is_zero_when_snapshot_field_is_missing():
    points = [
        AccountHistoryPoint(
            1,
            date(2026, 9, 23),
            Decimal("98500"),
        )
    ]

    assert AccountComparisonTab._transform_account_history(
        points, "Day's Gain/Loss"
    ) == [Decimal("0")]
    assert AccountComparisonTab._transform_account_history(
        points, "% Day's Gain/Loss"
    ) == [Decimal("0")]


def test_account_history_filters_weekends_and_holidays_from_performance_views():
    points = [
        AccountHistoryPoint(1, date(2026, 9, 18), Decimal("100000")),
        AccountHistoryPoint(1, date(2026, 9, 20), Decimal("100000")),
        AccountHistoryPoint(1, date(2026, 9, 21), Decimal("101000")),
        AccountHistoryPoint(2, date(2026, 9, 20), Decimal("200000")),
    ]

    trading_days = {date(2026, 9, 18), date(2026, 9, 21)}

    filtered = AccountComparisonTab._filter_to_trading_days(
        {1: points[:3], 2: points[3:]},
        trading_days,
    )

    assert [point.snapshot_date for point in filtered[1]] == [
        date(2026, 9, 18),
        date(2026, 9, 21),
    ]
    assert filtered[2] == []
