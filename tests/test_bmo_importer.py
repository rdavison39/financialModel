"""
Tests for the BMO Excel importer.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.importers.bmo_importer import BMOImporter


BMO_FILE = Path("data/uploads/Bmo-1.xlsx")


def test_bmo_importer_reads_account():
    """The importer reads the BMO account information."""
    result = BMOImporter(BMO_FILE).import_file()

    assert result.account_number == "21033605"


def test_bmo_importer_reads_snapshot_date():
    """The importer reads the snapshot date and time."""
    result = BMOImporter(BMO_FILE).import_file()

    assert result.snapshot_date == datetime(
        2026,
        9,
        11,
        15,
        59,
        7,
    )


def test_bmo_importer_reads_cash():
    """The importer reads both CAD and USD cash."""
    result = BMOImporter(BMO_FILE).import_file()

    assert len(result.cash) == 2

    cash = {
        item.currency: item.amount
        for item in result.cash
    }

    assert cash["CAD"] == Decimal("2101.22")
    assert cash["USD"] == Decimal("178.76")


def test_bmo_importer_reads_holdings():
    """The importer reads all BMO holdings."""
    result = BMOImporter(BMO_FILE).import_file()

    assert len(result.holdings) == 7


def test_bmo_importer_reads_holding_details():
    """The importer reads holding quantities, prices and values."""
    result = BMOImporter(BMO_FILE).import_file()

    holdings = {
        holding.symbol: holding
        for holding in result.holdings
    }

    assert holdings["BAM:CA"].quantity == Decimal("947")
    assert holdings["BAM:CA"].price == Decimal("65.46")
    assert holdings["BAM:CA"].market_value == Decimal("61990.62")
    assert holdings["BAM:CA"].currency == "CAD"

    assert holdings["BN:CA"].quantity == Decimal("5634")
    assert holdings["BN:CA"].price == Decimal("52.95")
    assert holdings["BN:CA"].market_value == Decimal("298320.30")
    assert holdings["BN:CA"].currency == "CAD"

    assert holdings["BCE:CA"].quantity == Decimal("2000")
    assert holdings["BCE:CA"].price == Decimal("32.42")
    assert holdings["BCE:CA"].market_value == Decimal("64840")
    assert holdings["BCE:CA"].currency == "CAD"

    assert holdings["BPO.PR.N:CA"].quantity == Decimal("3900")
    assert holdings["BPO.PR.N:CA"].price == Decimal("23.06")
    assert holdings["BPO.PR.N:CA"].market_value == Decimal("89934")
    assert holdings["BPO.PR.N:CA"].currency == "CAD"

    assert holdings["ENGH:CA"].quantity == Decimal("1450")
    assert holdings["ENGH:CA"].price == Decimal("16.60")
    assert holdings["ENGH:CA"].market_value == Decimal("24070")
    assert holdings["ENGH:CA"].currency == "CAD"

    assert holdings["NWC:CA"].quantity == Decimal("230")
    assert holdings["NWC:CA"].price == Decimal("51.78")
    assert holdings["NWC:CA"].market_value == Decimal("11909.40")
    assert holdings["NWC:CA"].currency == "CAD"

    assert holdings["FLG:US"].quantity == Decimal("6000")
    assert holdings["FLG:US"].price == Decimal("13.17")
    assert holdings["FLG:US"].market_value == Decimal("109561.23")
    assert holdings["FLG:US"].currency == "CAD"


def test_bmo_importer_reads_brokerage_snapshot_values():
    """
    The importer reads the additional values supplied by BMO.

    These values are authoritative brokerage data and must arrive in the
    importer DTO as Decimal values. We deliberately do not reconstruct
    them from quantity, price, or market value.
    """
    result = BMOImporter(BMO_FILE).import_file()

    assert result.holdings

    for holding in result.holdings:
        assert isinstance(holding.average_cost, Decimal)
        assert isinstance(holding.unrealized_gain, Decimal)
        assert isinstance(holding.unrealized_gain_percent, Decimal)
        assert isinstance(holding.daily_change, Decimal)
        assert isinstance(holding.daily_change_percent, Decimal)
        assert isinstance(holding.previous_close, Decimal)


def test_bmo_importer_preserves_brokerage_values_for_bam():
    """
    The BAM holding contains all newly imported brokerage fields.

    This test checks that the values are present as Decimal data without
    assuming values that are not established by the current test fixture.
    """
    result = BMOImporter(BMO_FILE).import_file()

    bam = next(
        holding
        for holding in result.holdings
        if holding.symbol == "BAM:CA"
    )

    assert bam.average_cost is not None
    assert bam.unrealized_gain is not None
    assert bam.unrealized_gain_percent is not None
    assert bam.daily_change is not None
    assert bam.daily_change_percent is not None
    assert bam.previous_close is not None
