"""
Unit tests for excel_reader.py
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.importers.excel_reader import ExcelReader
from src.importers.worksheet_helper import WorksheetHelper


def test_filename(
    bmo_workbook_path: Path,
) -> None:
    reader = ExcelReader(bmo_workbook_path)

    assert reader.filename == bmo_workbook_path


def test_open(
    bmo_workbook_path: Path,
) -> None:
    reader = ExcelReader(bmo_workbook_path)

    reader.open()

    assert reader.workbook is not None

    reader.close()


def test_sheet_names(
    bmo_workbook_path: Path,
) -> None:
    reader = ExcelReader(bmo_workbook_path)

    reader.open()

    assert reader.sheet_names == ["Holdings"]

    reader.close()


def test_worksheet_count(
    bmo_workbook_path: Path,
) -> None:
    reader = ExcelReader(bmo_workbook_path)

    reader.open()

    assert reader.worksheet_count == 1

    reader.close()


def test_first_worksheet(
    bmo_workbook_path: Path,
) -> None:
    reader = ExcelReader(bmo_workbook_path)

    reader.open()

    sheet = reader.first_worksheet

    assert isinstance(sheet, WorksheetHelper)

    reader.close()


def test_get_worksheet(
    bmo_workbook_path: Path,
) -> None:
    reader = ExcelReader(bmo_workbook_path)

    reader.open()

    sheet = reader.get_worksheet("Holdings")

    assert isinstance(sheet, WorksheetHelper)

    reader.close()


def test_missing_file() -> None:
    reader = ExcelReader("does_not_exist.xlsx")

    with pytest.raises(FileNotFoundError):
        reader.open()


def test_invalid_sheet_name(
    bmo_workbook_path: Path,
) -> None:
    reader = ExcelReader(bmo_workbook_path)

    reader.open()

    with pytest.raises(KeyError):
        reader.get_worksheet("XYZ")

    reader.close()


def test_context_manager(
    bmo_workbook_path: Path,
) -> None:
    with ExcelReader(bmo_workbook_path) as reader:
        assert reader.worksheet_count == 1