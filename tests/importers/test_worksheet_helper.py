"""
Unit tests for worksheet_helper.py
"""

from __future__ import annotations

from src.importers.worksheet_helper import WorksheetHelper


def test_max_row(
    bmo_sheet: WorksheetHelper,
) -> None:
    assert bmo_sheet.max_row > 0


def test_max_column(
    bmo_sheet: WorksheetHelper,
) -> None:
    assert bmo_sheet.max_column > 0


def test_cell_text(
    bmo_sheet: WorksheetHelper,
) -> None:
    text = bmo_sheet.cell_text(1, 6)

    assert text.startswith("Portfolio report")


def test_cell_value(
    bmo_sheet: WorksheetHelper,
) -> None:
    value = bmo_sheet.cell_value(4, 3)

    assert value is not None


def test_row_values(
    bmo_sheet: WorksheetHelper,
) -> None:
    values = bmo_sheet.row_values(1)

    assert len(values) == bmo_sheet.max_column


def test_row_text(
    bmo_sheet: WorksheetHelper,
) -> None:
    values = bmo_sheet.row_text(1)

    assert len(values) == bmo_sheet.max_column

    assert any(
        "Portfolio report" in value
        for value in values
    )


def test_find_text(
    bmo_sheet: WorksheetHelper,
) -> None:
    row, column = bmo_sheet.find_text(
        "Cash Details"
    )

    assert row > 0
    assert column > 0


def test_find_text_case_insensitive(
    bmo_sheet: WorksheetHelper,
) -> None:
    row, column = bmo_sheet.find_text(
        "cash details"
    )

    assert row > 0
    assert column > 0


def test_find_text_in_row(
    bmo_sheet: WorksheetHelper,
) -> None:
    row, _ = bmo_sheet.find_text(
        "Holding Details"
    )

    header_row = row + 1

    column = bmo_sheet.find_text_in_row(
        "Symbol",
        header_row,
    )

    assert column is not None
    assert column > 0


def test_find_text_in_column(
    bmo_sheet: WorksheetHelper,
) -> None:
    row = bmo_sheet.find_text_in_column(
        "CAD",
        1,
    )

    assert row is not None


def test_is_empty_row(
    bmo_sheet: WorksheetHelper,
) -> None:
    assert bmo_sheet.is_empty_row(8)


def test_non_empty_row(
    bmo_sheet: WorksheetHelper,
) -> None:
    assert not bmo_sheet.is_empty_row(1)


def test_cell_outside_sheet(
    bmo_sheet: WorksheetHelper,
) -> None:
    assert (
        bmo_sheet.cell_value(
            10000,
            10000,
        )
        is None
    )


def test_cell_text_outside_sheet(
    bmo_sheet: WorksheetHelper,
) -> None:
    assert (
        bmo_sheet.cell_text(
            10000,
            10000,
        )
        == ""
    )