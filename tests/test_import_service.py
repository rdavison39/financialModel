"""
Tests for the import service.
"""

from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from src.importers.bmo_importer import BMOImporter
from src.importers.nesbitt_importer import NesbittImporter
from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.cash_snapshot import CashSnapshot
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord
from src.services.import_service import ImportService


BMO_FILE = Path("data/uploads/Bmo-1.xlsx")
NESBITT_FILE = Path("data/uploads/Nesbit-1.xlsx")


def test_import_bmo_creates_brokerage_account_and_data(session):
    """Importing BMO creates all required database records."""

    imported_account = BMOImporter(BMO_FILE).import_file()

    service = ImportService(session)

    result = service.import_snapshot(
        brokerage_name="BMO",
        imported_account=imported_account,
        file_name="Bmo-1.xlsx",
    )

    assert result.account_number == "21033605"
    assert result.holdings_imported == 7
    assert result.cash_imported == 2
    assert result.duplicate is False

    brokerage = session.scalar(
        select(Brokerage).where(Brokerage.name == "BMO")
    )

    assert brokerage is not None

    account = session.scalar(
        select(Account).where(
            Account.account_number == "21033605"
        )
    )

    assert account is not None
    assert account.brokerage_id == brokerage.id

    holdings = session.scalars(
        select(HoldingSnapshot).where(
            HoldingSnapshot.account_id == account.id
        )
    ).all()

    cash = session.scalars(
        select(CashSnapshot).where(
            CashSnapshot.account_id == account.id
        )
    ).all()

    assert len(holdings) == 7
    assert len(cash) == 2


def test_import_bmo_creates_companies(session):
    """Importing BMO creates companies for each security."""

    imported_account = BMOImporter(BMO_FILE).import_file()

    service = ImportService(session)

    service.import_snapshot(
        brokerage_name="BMO",
        imported_account=imported_account,
        file_name="Bmo-1.xlsx",
    )

    companies = session.scalars(
        select(Company)
    ).all()

    symbols = {company.symbol for company in companies}

    assert symbols == {
        "BAM:CA",
        "BN:CA",
        "BCE:CA",
        "BPO.PR.N:CA",
        "ENGH:CA",
        "NWC:CA",
        "FLG:US",
    }


def test_import_bmo_stores_import_record(session):
    """Importing BMO creates an import record."""

    imported_account = BMOImporter(BMO_FILE).import_file()

    service = ImportService(session)

    service.import_snapshot(
        brokerage_name="BMO",
        imported_account=imported_account,
        file_name="Bmo-1.xlsx",
    )

    record = session.scalar(
        select(ImportRecord)
    )

    assert record is not None
    assert record.file_name == "Bmo-1.xlsx"
    assert record.snapshot_date == imported_account.snapshot_date


def test_duplicate_import_is_rejected(session):
    """The same brokerage snapshot cannot be imported twice."""

    imported_account = BMOImporter(BMO_FILE).import_file()

    service = ImportService(session)

    first_result = service.import_snapshot(
        brokerage_name="BMO",
        imported_account=imported_account,
        file_name="Bmo-1.xlsx",
    )

    second_result = service.import_snapshot(
        brokerage_name="BMO",
        imported_account=imported_account,
        file_name="Bmo-1.xlsx",
    )

    assert first_result.duplicate is False
    assert second_result.duplicate is True
    assert second_result.holdings_imported == 0
    assert second_result.cash_imported == 0

    records = session.scalars(
        select(ImportRecord)
    ).all()

    assert len(records) == 1


def test_import_two_brokerages_creates_separate_accounts(session):
    """BMO and Nesbitt imports create separate brokerage accounts."""

    bmo_account = BMOImporter(BMO_FILE).import_file()
    nesbitt_account = NesbittImporter(NESBITT_FILE).import_file()

    service = ImportService(session)

    bmo_result = service.import_snapshot(
        brokerage_name="BMO",
        imported_account=bmo_account,
        file_name="Bmo-1.xlsx",
    )

    nesbitt_result = service.import_snapshot(
        brokerage_name="Nesbitt Burns",
        imported_account=nesbitt_account,
        file_name="Nesbit-1.xlsx",
    )

    assert bmo_result.account_number == "21033605"
    assert nesbitt_result.account_number == "70558197"

    accounts = session.scalars(
        select(Account).order_by(Account.id)
    ).all()

    assert len(accounts) == 2

    brokerages = session.scalars(
        select(Brokerage).order_by(Brokerage.id)
    ).all()

    assert len(brokerages) == 2

    assert {brokerage.name for brokerage in brokerages} == {
        "BMO",
        "Nesbitt Burns",
    }


def test_import_preserves_decimal_values(session):
    """Imported financial values are stored as Decimal values."""

    imported_account = BMOImporter(BMO_FILE).import_file()

    service = ImportService(session)

    service.import_snapshot(
        brokerage_name="BMO",
        imported_account=imported_account,
        file_name="Bmo-1.xlsx",
    )

    holding = session.scalar(
        select(HoldingSnapshot).where(
            HoldingSnapshot.quantity == Decimal("947")
        )
    )

    assert holding is not None
    assert holding.quantity == Decimal("947")
    assert holding.price == Decimal("65.46")
    assert holding.market_value == Decimal("61990.62")

    cash = session.scalar(
        select(CashSnapshot).where(
            CashSnapshot.currency == "CAD"
        )
    )

    assert cash is not None
    assert cash.amount == Decimal("2101.22")