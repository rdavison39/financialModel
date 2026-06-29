"""
Unit tests for bmo_investorline_importer.py
"""

from __future__ import annotations

from src.dto.imported_account import ImportedAccount
from src.importers.bmo_investorline_importer import (
    BMOInvestorLineImporter,
)


def test_import_returns_account(
    bmo_workbook_path,
) -> None:

    importer = BMOInvestorLineImporter(
        bmo_workbook_path,
    )

    account = importer.import_account()

    assert isinstance(
        account,
        ImportedAccount,
    )


def test_account_information(
    bmo_workbook_path,
) -> None:

    importer = BMOInvestorLineImporter(
        bmo_workbook_path,
    )

    account = importer.import_account()

    assert account.account_number == "22427503"
    assert account.account_type == "TFSA"
    assert account.account_name == "BMO TFSA"


def test_statement_date(
    bmo_workbook_path,
) -> None:

    importer = BMOInvestorLineImporter(
        bmo_workbook_path,
    )

    account = importer.import_account()

    assert account.statement_date.year == 2026
    assert account.statement_date.month == 6
    assert account.statement_date.day == 28


def test_cash_imported(
    bmo_workbook_path,
) -> None:

    importer = BMOInvestorLineImporter(
        bmo_workbook_path,
    )

    account = importer.import_account()

    assert len(account.cash) > 0


def test_positions_imported(
    bmo_workbook_path,
) -> None:

    importer = BMOInvestorLineImporter(
        bmo_workbook_path,
    )

    account = importer.import_account()

    assert len(account.positions) > 0


def test_cash_contains_valid_values(
    bmo_workbook_path,
) -> None:

    importer = BMOInvestorLineImporter(
        bmo_workbook_path,
    )

    account = importer.import_account()

    for cash in account.cash:

        assert cash.currency != ""

        assert cash.amount is not None


def test_positions_contain_valid_values(
    bmo_workbook_path,
) -> None:

    importer = BMOInvestorLineImporter(
        bmo_workbook_path,
    )

    account = importer.import_account()

    for position in account.positions:

        assert position.symbol != ""

        assert position.description != ""

        assert position.quantity >= 0

        assert position.unit_price >= 0

        assert position.market_value >= 0

        assert position.cost_basis >= 0


def test_position_has_currency(
    bmo_workbook_path,
) -> None:

    importer = BMOInvestorLineImporter(
        bmo_workbook_path,
    )

    account = importer.import_account()

    for position in account.positions:

        assert position.currency != ""


def test_import_is_repeatable(
    bmo_workbook_path,
) -> None:

    importer = BMOInvestorLineImporter(
        bmo_workbook_path,
    )

    account1 = importer.import_account()

    account2 = importer.import_account()

    assert (
        account1.account_number
        == account2.account_number
    )

    assert (
        len(account1.cash)
        == len(account2.cash)
    )

    assert (
        len(account1.positions)
        == len(account2.positions)
    )