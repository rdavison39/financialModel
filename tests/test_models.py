"""
Tests for the database models.
"""

from decimal import Decimal

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.cash_snapshot import CashSnapshot
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord
from src.models.portfolio_snapshot import PortfolioSnapshot


def test_create_brokerage(session):
    """A brokerage can be stored in the database."""

    brokerage = Brokerage(name="BMO")

    session.add(brokerage)
    session.commit()

    assert brokerage.id is not None
    assert brokerage.name == "BMO"


def test_create_account(session):
    """An account can be stored in the database."""

    brokerage = Brokerage(name="BMO")
    session.add(brokerage)
    session.commit()

    account = Account(
        brokerage_id=brokerage.id,
        account_number="21033605",
        name="My BMO Account",
    )

    session.add(account)
    session.commit()

    assert account.id is not None
    assert account.account_number == "21033605"
    assert account.name == "My BMO Account"


def test_create_company(session):
    """A company can be stored in the database."""

    company = Company(
        symbol="BAM:CA",
        name="Brookfield Asset Management",
    )

    session.add(company)
    session.commit()

    assert company.id is not None
    assert company.symbol == "BAM:CA"


def test_create_holding_snapshot(session):
    """A holding snapshot can be stored."""

    brokerage = Brokerage(name="BMO")
    session.add(brokerage)
    session.commit()

    account = Account(
        brokerage_id=brokerage.id,
        account_number="21033605",
        name="BMO Account",
    )

    company = Company(
        symbol="BAM:CA",
        name="Brookfield Asset Management",
    )

    session.add_all([account, company])
    session.commit()

    from datetime import datetime

    snapshot = HoldingSnapshot(
        account_id=account.id,
        company_id=company.id,
        snapshot_date=datetime(2026, 9, 15, 15, 59, 7),
        quantity=Decimal("947"),
        price=Decimal("65.46"),
        market_value=Decimal("61990.62"),
        currency="CAD",
    )

    session.add(snapshot)
    session.commit()

    assert snapshot.id is not None
    assert snapshot.quantity == Decimal("947")
    assert snapshot.market_value == Decimal("61990.62")


def test_create_cash_snapshot(session):
    """A cash snapshot can be stored."""

    brokerage = Brokerage(name="BMO")
    session.add(brokerage)
    session.commit()

    account = Account(
        brokerage_id=brokerage.id,
        account_number="21033605",
        name="BMO Account",
    )

    session.add(account)
    session.commit()

    from datetime import datetime

    snapshot = CashSnapshot(
        account_id=account.id,
        snapshot_date=datetime(2026, 9, 15, 15, 59, 7),
        currency="CAD",
        amount=Decimal("2101.22"),
    )

    session.add(snapshot)
    session.commit()

    assert snapshot.id is not None
    assert snapshot.amount == Decimal("2101.22")


def test_create_import_record(session):
    """An import record can be stored."""

    brokerage = Brokerage(name="BMO")
    session.add(brokerage)
    session.commit()

    account = Account(
        brokerage_id=brokerage.id,
        account_number="21033605",
        name="BMO Account",
    )

    session.add(account)
    session.commit()

    from datetime import datetime

    record = ImportRecord(
        brokerage_id=brokerage.id,
        account_id=account.id,
        snapshot_date=datetime(2026, 9, 15, 15, 59, 7),
        file_name="Bmo-1.xlsx",
    )

    session.add(record)
    session.commit()

    assert record.id is not None
    assert record.file_name == "Bmo-1.xlsx"


def test_create_account_portfolio_snapshot(session):
    """An account portfolio snapshot can be stored."""

    brokerage = Brokerage(name="BMO")
    session.add(brokerage)
    session.commit()

    account = Account(
        brokerage_id=brokerage.id,
        account_number="21033605",
        name="BMO Account",
    )

    session.add(account)
    session.commit()

    from datetime import date

    snapshot = PortfolioSnapshot(
        account_id=account.id,
        snapshot_date=date(2026, 9, 15),
        total_value=Decimal("624424.25"),
    )

    session.add(snapshot)
    session.commit()

    assert snapshot.id is not None
    assert snapshot.total_value == Decimal("624424.25")


def test_create_consolidated_portfolio_snapshot(session):
    """A consolidated portfolio snapshot can be stored."""

    from datetime import date

    snapshot = PortfolioSnapshot(
        account_id=None,
        snapshot_date=date(2026, 9, 15),
        total_value=Decimal("1070709.25"),
    )

    session.add(snapshot)
    session.commit()

    assert snapshot.id is not None
    assert snapshot.account_id is None
    assert snapshot.total_value == Decimal("1070709.25")