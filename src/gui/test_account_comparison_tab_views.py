"""Tests for Account History chart view transformations."""

from datetime import date
from decimal import Decimal

from src.gui.account_comparison_tab import AccountComparisonTab
from src.services.account_comparison_history_service import AccountHistoryPoint
from src.services.portfolio_history_service import BenchmarkHistoryPoint


def make_points():
    return [
        AccountHistoryPoint(
            account_id=1,
            snapshot_date=date(2026, 9, 17),
            total_value=Decimal("100000"),
            daily_change=Decimal("1000"),
            daily_change_percent=Decimal("1.010101"),
        ),
        AccountHistoryPoint(
            account_id=1,
            snapshot_date=date(2026, 9, 18),
            total_value=Decimal("99000"),
            daily_change=Decimal("-1000"),
            daily_change_percent=Decimal("-1.000000"),
        ),
        AccountHistoryPoint(
            account_id=1,
            snapshot_date=date(2026, 9, 21),
            total_value=Decimal("101000"),
            daily_change=Decimal("2000"),
            daily_change_percent=Decimal("2.020202"),
        ),
    ]


def test_account_history_view_transformations():
    points = make_points()

    assert AccountComparisonTab._transform_account_history(
        points, "Dollar Value"
    ) == [Decimal("100000"), Decimal("99000"), Decimal("101000")]

    assert AccountComparisonTab._transform_account_history(
        points, "Gain/Loss"
    ) == [Decimal("0"), Decimal("-1000"), Decimal("1000")]

    growth = AccountComparisonTab._transform_account_history(points, "% Growth")
    assert growth == [Decimal("0"), Decimal("-1"), Decimal("1")]

    assert AccountComparisonTab._transform_account_history(
        points, "Daily Change"
    ) == [Decimal("1000"), Decimal("-1000"), Decimal("2000")]

    assert AccountComparisonTab._transform_account_history(
        points, "% Daily Change"
    ) == [
        Decimal("1.010101"),
        Decimal("-1.000000"),
        Decimal("2.020202"),
    ]


def test_account_history_daily_fallbacks_when_snapshot_daily_fields_are_missing():
    points = [
        AccountHistoryPoint(1, date(2026, 9, 17), Decimal("100000")),
        AccountHistoryPoint(1, date(2026, 9, 18), Decimal("99000")),
        AccountHistoryPoint(1, date(2026, 9, 21), Decimal("101000")),
    ]

    assert AccountComparisonTab._transform_account_history(
        points, "Daily Change"
    ) == [Decimal("0"), Decimal("-1000"), Decimal("2000")]

    daily_percent = AccountComparisonTab._transform_account_history(
        points, "% Daily Change"
    )
    assert daily_percent[0] == Decimal("0")
    assert daily_percent[1] == Decimal("-1")
    assert daily_percent[2] == Decimal("2000") / Decimal("99000") * Decimal("100")


def test_benchmark_daily_change_uses_previous_close_before_selected_range():
    tab = AccountComparisonTab.__new__(AccountComparisonTab)
    tab._benchmark_previous_value = Decimal("100")
    tab._last_benchmark = [
        BenchmarkHistoryPoint(date(2026, 9, 17), Decimal("101")),
        BenchmarkHistoryPoint(date(2026, 9, 18), Decimal("99")),
        BenchmarkHistoryPoint(date(2026, 9, 21), Decimal("102")),
    ]

    result = tab._benchmark_daily_change_percent_values()

    assert result == [
        Decimal("1"),
        Decimal("-2") / Decimal("101") * Decimal("100"),
        Decimal("3") / Decimal("99") * Decimal("100"),
    ]
