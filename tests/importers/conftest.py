"""
Shared pytest fixtures for importer tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.importers.bmo_layout import BMOLayout
from src.importers.excel_reader import ExcelReader
from src.importers.worksheet_helper import WorksheetHelper


@pytest.fixture(scope="session")
def bmo_workbook_path() -> Path:
    """
    Path to the sample BMO InvestorLine workbook.
    """

    return (
        Path(__file__).parent.parent
        / "data"
        / "bmo"
        / "MyHoldings_22427503.xlsx"
    )


@pytest.fixture
def excel_reader(
    bmo_workbook_path: Path,
) -> ExcelReader:
    """
    Open Excel workbook.
    """

    with ExcelReader(bmo_workbook_path) as reader:
        yield reader


@pytest.fixture
def bmo_sheet(
    excel_reader: ExcelReader,
) -> WorksheetHelper:
    """
    First worksheet from the workbook.
    """

    return excel_reader.first_worksheet


@pytest.fixture
def bmo_layout(
    bmo_sheet: WorksheetHelper,
) -> BMOLayout:
    """
    Discovered worksheet layout.
    """

    return BMOLayout.discover(bmo_sheet)