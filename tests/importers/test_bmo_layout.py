"""
Unit tests for bmo_layout.py
"""

from __future__ import annotations

from datetime import date

from src.importers.bmo_layout import BMOLayout
from src.importers.worksheet_helper import WorksheetHelper


def test_discover_returns_layout(
    bmo_sheet: WorksheetHelper,
) -> None:

    layout = BMOLayout.discover(
        bmo_sheet,
    )

    assert isinstance(
        layout,
        BMOLayout,
    )


def test_account_number(
    bmo_layout: BMOLayout,
) -> None:

    assert (
        bmo_layout.account_number
        == "22427503"
    )


def test_account_type(
    bmo_layout: BMOLayout,
) -> None:

    assert (
        bmo_layout.account_type
        == "TFSA"
    )


def test_statement_date(
    bmo_layout: BMOLayout,
) -> None:

    assert (
        bmo_layout.statement_date
        == date(
            2026,
            6,
            28,
        )
    )


def test_cash_section_rows(
    bmo_layout: BMOLayout,
) -> None:

    assert bmo_layout.cash_header_row > 0
    assert (
        bmo_layout.cash_data_row
        == bmo_layout.cash_header_row + 1
    )


def test_holdings_section_rows(
    bmo_layout: BMOLayout,
) -> None:

    assert bmo_layout.holdings_header_row > 0
    assert (
        bmo_layout.holdings_data_row
        == bmo_layout.holdings_header_row + 1
    )


def test_cash_columns(
    bmo_layout: BMOLayout,
) -> None:

    assert bmo_layout.currency_column > 0
    assert bmo_layout.cash_column > 0


def test_position_columns(
    bmo_layout: BMOLayout,
) -> None:

    assert bmo_layout.symbol_column > 0

    assert (
        bmo_layout.description_column
        > 0
    )

    assert (
        bmo_layout.quantity_column
        > 0
    )

    assert (
        bmo_layout.current_price_column
        > 0
    )

    assert (
        bmo_layout.total_cost_column
        > 0
    )

    assert (
        bmo_layout.market_value_column
        > 0
    )

    assert (
        bmo_layout.asset_class_column
        > 0
    )

    assert (
        bmo_layout.settlement_currency_column
        > 0
    )


def test_column_order(
    bmo_layout: BMOLayout,
) -> None:

    assert (
        bmo_layout.symbol_column
        < bmo_layout.description_column
        < bmo_layout.quantity_column
        < bmo_layout.current_price_column
        < bmo_layout.total_cost_column
        < bmo_layout.market_value_column
    )


def test_layout_is_immutable(
    bmo_layout: BMOLayout,
) -> None:

    try:
        bmo_layout.account_number = "123"
        modified = True
    except Exception:
        modified = False

    assert modified is False