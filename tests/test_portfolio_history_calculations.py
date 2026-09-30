from datetime import date
from decimal import Decimal

from src.services.portfolio_history_service import (
    BenchmarkHistoryPoint,
    PortfolioHistoryPoint,
    PortfolioHistoryService,
)


def _history_points():
    return [
        PortfolioHistoryPoint(date(2026, 9, 17), Decimal("1000")),
        PortfolioHistoryPoint(date(2026, 9, 18), Decimal("990")),
        PortfolioHistoryPoint(date(2026, 9, 21), Decimal("1010")),
    ]


def test_shared_portfolio_metric_calculations():
    history = _history_points()

    assert PortfolioHistoryService.calculate_metric_values(
        history, "% Growth Since Start"
    ) == [Decimal("0"), Decimal("-1"), Decimal("1")]

    assert PortfolioHistoryService.calculate_metric_values(
        history, "Day's Gain/Loss"
    ) == [Decimal("0"), Decimal("-10"), Decimal("10")]

    daily_percent = PortfolioHistoryService.calculate_metric_values(
        history, "% Day's Gain/Loss"
    )
    assert daily_percent[0] == Decimal("0")
    assert daily_percent[1] == Decimal("-1")
    assert daily_percent[2] == (
        (Decimal("1010") - Decimal("990")) / Decimal("990") * Decimal("100")
    )


def test_shared_effective_date_range_uses_actual_history():
    history = _history_points()

    assert PortfolioHistoryService.calculate_effective_date_range(
        date(2025, 9, 29),
        date(2026, 9, 29),
        history,
    ) == (date(2026, 9, 17), date(2026, 9, 21))


def test_shared_benchmark_growth_and_daily_returns():
    benchmark = [
        BenchmarkHistoryPoint(date(2026, 9, 17), Decimal("100")),
        BenchmarkHistoryPoint(date(2026, 9, 18), Decimal("99.5")),
        BenchmarkHistoryPoint(date(2026, 9, 21), Decimal("100.5")),
    ]

    assert PortfolioHistoryService.calculate_benchmark_growth(benchmark) == [
        Decimal("0"),
        Decimal("-0.5"),
        Decimal("0.5"),
    ]

    daily = PortfolioHistoryService.calculate_benchmark_daily_change_percent_values(
        benchmark, Decimal("100")
    )
    assert daily[0] == Decimal("0")
    assert daily[1] == Decimal("-0.5")
    assert daily[2] == (
        Decimal("100.5") - Decimal("99.5")
    ) / Decimal("99.5") * Decimal("100")


def test_benchmark_effective_range_and_prior_close_are_shared():
    benchmark = [
        BenchmarkHistoryPoint(date(2026, 9, 16), Decimal("98")),
        BenchmarkHistoryPoint(date(2026, 9, 17), Decimal("100")),
        BenchmarkHistoryPoint(date(2026, 9, 18), Decimal("99.5")),
        BenchmarkHistoryPoint(date(2026, 9, 21), Decimal("100.5")),
    ]

    assert PortfolioHistoryService.calculate_benchmark_query_start(
        date(2026, 9, 17), daily_change_view=False
    ) == date(2026, 9, 17)
    assert PortfolioHistoryService.calculate_benchmark_query_start(
        date(2026, 9, 17), daily_change_view=True
    ) == date(2026, 9, 3)

    filtered, previous_close = PortfolioHistoryService.filter_benchmark_history(
        benchmark, date(2026, 9, 17), date(2026, 9, 21)
    )
    assert [point.snapshot_date for point in filtered] == [
        date(2026, 9, 17),
        date(2026, 9, 18),
        date(2026, 9, 21),
    ]
    assert previous_close == Decimal("98")


def test_shared_metric_dispatch_supports_current_and_legacy_names():
    history = _history_points()

    assert PortfolioHistoryService.calculate_metric_values(
        history, "Portfolio Value"
    ) == PortfolioHistoryService.calculate_metric_values(history, "Dollar Value")

    assert PortfolioHistoryService.calculate_metric_values(
        history, "% Growth Since Start"
    ) == PortfolioHistoryService.calculate_metric_values(history, "% Growth")

    assert PortfolioHistoryService.calculate_metric_values(
        history, "Day's Gain/Loss"
    ) == PortfolioHistoryService.calculate_metric_values(history, "Gain/Loss")

    assert PortfolioHistoryService.calculate_metric_values(
        history, "Daily Change"
    ) == PortfolioHistoryService.calculate_daily_change_values(history)
