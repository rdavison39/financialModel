"""
Tests for the Nesbitt Burns Excel importer.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.importers.nesbitt_importer import NesbittImporter


NESBITT_FILE = Path("data/uploads/Nesbit-1.xlsx")
CASH_ONLY_1 = Path(
    r"C:\Users\ronal\Downloads\nesbitt\MyHoldings_70556033.xlsx"
)
CASH_ONLY_2 = Path(
    r"C:\Users\ronal\Downloads\nesbitt\MyHoldings_70556060.xlsx"
)


def test_importer_reads_account_number():
    """Importer reads the account number."""

    imported = NesbittImporter(NESBITT_FILE).import_file()

    assert imported.account_number == "70558197"


def test_importer_reads_snapshot_date():
    """Importer reads the snapshot date."""

    imported = NesbittImporter(NESBITT_FILE).import_file()

    assert imported.snapshot_date == datetime(
        2026,
        9,
        15,
        15,
        4,
        56,
    )


def test_importer_reads_cash():
    """Importer reads CAD and USD cash."""

    imported = NesbittImporter(NESBITT_FILE).import_file()

    assert len(imported.cash) == 2

    cash = {
        item.currency: item.amount
        for item in imported.cash
    }

    assert cash["CAD"] == Decimal("2615.48")
    assert cash["USD"] == Decimal("1317.30")


def test_importer_reads_holdings():
    """Importer reads all security holdings."""

    imported = NesbittImporter(NESBITT_FILE).import_file()

    assert len(imported.holdings) == 50


def test_importer_skips_cash_rows_from_holdings():
    """Cash rows are not imported as security holdings."""

    imported = NesbittImporter(NESBITT_FILE).import_file()

    symbols = {holding.symbol for holding in imported.holdings}

    assert "CANADIAN DOLLAR" not in symbols
    assert "US DOLLAR" not in symbols


def test_importer_reads_known_holdings():
    """Importer reads representative security holdings correctly."""

    imported = NesbittImporter(NESBITT_FILE).import_file()

    holdings = {
        holding.symbol: holding
        for holding in imported.holdings
    }

    assert holdings["GRT.UN:CA"].quantity > 0
    assert holdings["GRT.UN:CA"].price > 0
    assert holdings["GRT.UN:CA"].market_value > 0

    assert holdings["CTC.A:CA"].quantity > 0
    assert holdings["CTC.A:CA"].price > 0
    assert holdings["CTC.A:CA"].market_value > 0

    assert holdings["RCI.B:CA"].quantity > 0
    assert holdings["RCI.B:CA"].price > 0
    assert holdings["RCI.B:CA"].market_value > 0


def test_nesbitt_importer_reads_brokerage_snapshot_values():
    """Importer reads all brokerage-supplied snapshot values."""

    imported = NesbittImporter(NESBITT_FILE).import_file()

    for holding in imported.holdings:
        assert isinstance(holding.average_cost, Decimal)
        assert isinstance(holding.unrealized_gain, Decimal)
        assert isinstance(holding.unrealized_gain_percent, Decimal)
        assert isinstance(holding.daily_change, Decimal)
        assert isinstance(holding.daily_change_percent, Decimal)
        assert isinstance(holding.previous_close, Decimal)


def test_nesbitt_importer_preserves_brokerage_values_for_grt():
    """Representative holding contains the brokerage-supplied fields."""

    imported = NesbittImporter(NESBITT_FILE).import_file()

    holdings = {
        holding.symbol: holding
        for holding in imported.holdings
    }

    holding = holdings["GRT.UN:CA"]

    assert holding.average_cost is not None
    assert holding.unrealized_gain is not None
    assert holding.unrealized_gain_percent is not None
    assert holding.daily_change is not None
    assert holding.daily_change_percent is not None
    assert holding.previous_close is not None


def test_cash_only_individual_account():
    """Cash-only individual account can be imported."""

    imported = NesbittImporter(CASH_ONLY_1).import_file()

    assert imported.account_number == "70556033"
    assert len(imported.holdings) == 0
    assert len(imported.cash) == 1

    cash = imported.cash[0]

    assert cash.currency == "USD"
    assert cash.amount == Decimal("27.74")


def test_cash_only_joint_account():
    """Cash-only joint account can be imported."""

    imported = NesbittImporter(CASH_ONLY_2).import_file()

    assert imported.account_number == "70556060"
    assert len(imported.holdings) == 0
    assert len(imported.cash) == 1

    cash = imported.cash[0]

    assert cash.currency == "USD"
    assert cash.amount == Decimal("89.93")


def test_cash_only_accounts_have_snapshot_date():
    """Cash-only reports receive a snapshot date."""

    imported_1 = NesbittImporter(CASH_ONLY_1).import_file()
    imported_2 = NesbittImporter(CASH_ONLY_2).import_file()

    assert imported_1.snapshot_date is not None
    assert imported_2.snapshot_date is not None
