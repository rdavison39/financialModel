"""
Tests for brokerage import/re-import rules.

Rules under test:
    1. First import creates one daily snapshot.
    2. Exact same source timestamp is skipped.
    3. Older same-day source timestamp is skipped.
    4. Newer same-day source timestamp replaces the existing snapshot.
    5. A different calendar day creates a new historical snapshot.
"""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from src.importers.bmo_importer import BMOImporter
from src.models.account import Account
from src.models.cash_snapshot import CashSnapshot
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord
from src.services.import_service import ImportService


BMO_FILE = Path("data/uploads/Bmo-1.xlsx")


def _load_bmo():
    return BMOImporter(BMO_FILE).import_file()


def _account(session, account_number: str) -> Account:
    account = session.scalar(
        select(Account).where(
            Account.account_number == account_number
        )
    )
    assert account is not None
    return account


def test_same_timestamp_is_skipped(session):
    imported = _load_bmo()
    service = ImportService(session)

    first = service.import_snapshot(
        "BMO",
        imported,
        "first.xlsx",
    )
    second = service.import_snapshot(
        "BMO",
        imported,
        "second.xlsx",
    )

    assert first.duplicate is False
    assert first.replaced is False
    assert second.duplicate is True
    assert second.replaced is False

    records = session.scalars(
        select(ImportRecord)
    ).all()

    assert len(records) == 1
    assert records[0].file_name == "first.xlsx"


def test_older_same_day_is_skipped(session):
    imported = _load_bmo()
    service = ImportService(session)

    service.import_snapshot(
        "BMO",
        imported,
        "newer.xlsx",
    )

    older = replace(
        imported,
        snapshot_date=imported.snapshot_date - timedelta(hours=1),
    )

    result = service.import_snapshot(
        "BMO",
        older,
        "older.xlsx",
    )

    assert result.duplicate is True
    assert result.replaced is False

    record = session.scalar(select(ImportRecord))

    assert record is not None
    assert record.file_name == "newer.xlsx"
    assert record.snapshot_date == imported.snapshot_date


def test_newer_same_day_replaces_existing_snapshot(session):
    imported = _load_bmo()
    service = ImportService(session)

    first = service.import_snapshot(
        "BMO",
        imported,
        "old.xlsx",
    )

    assert first.replaced is False

    account = _account(session, imported.account_number)

    old_holding_count = len(
        session.scalars(
            select(HoldingSnapshot).where(
                HoldingSnapshot.account_id == account.id,
                HoldingSnapshot.snapshot_date
                == imported.snapshot_date,
            )
        ).all()
    )

    old_cash_count = len(
        session.scalars(
            select(CashSnapshot).where(
                CashSnapshot.account_id == account.id,
                CashSnapshot.snapshot_date
                == imported.snapshot_date,
            )
        ).all()
    )

    assert old_holding_count == len(imported.holdings)
    assert old_cash_count == len(imported.cash)

    newer_timestamp = imported.snapshot_date + timedelta(
        minutes=5
    )

    newer = replace(
        imported,
        snapshot_date=newer_timestamp,
    )

    result = service.import_snapshot(
        "BMO",
        newer,
        "new.xlsx",
    )

    assert result.duplicate is False
    assert result.replaced is True

    records = session.scalars(
        select(ImportRecord)
    ).all()

    assert len(records) == 1
    assert records[0].file_name == "new.xlsx"
    assert records[0].snapshot_date == newer_timestamp
    assert records[0].snapshot_day == newer_timestamp.date()

    old_holdings = session.scalars(
        select(HoldingSnapshot).where(
            HoldingSnapshot.account_id == account.id,
            HoldingSnapshot.snapshot_date
            == imported.snapshot_date,
        )
    ).all()

    new_holdings = session.scalars(
        select(HoldingSnapshot).where(
            HoldingSnapshot.account_id == account.id,
            HoldingSnapshot.snapshot_date
            == newer_timestamp,
        )
    ).all()

    assert old_holdings == []
    assert len(new_holdings) == old_holding_count

    old_cash = session.scalars(
        select(CashSnapshot).where(
            CashSnapshot.account_id == account.id,
            CashSnapshot.snapshot_date
            == imported.snapshot_date,
        )
    ).all()

    new_cash = session.scalars(
        select(CashSnapshot).where(
            CashSnapshot.account_id == account.id,
            CashSnapshot.snapshot_date
            == newer_timestamp,
        )
    ).all()

    assert old_cash == []
    assert len(new_cash) == old_cash_count


def test_different_calendar_day_creates_new_snapshot(session):
    imported = _load_bmo()
    service = ImportService(session)

    first = service.import_snapshot(
        "BMO",
        imported,
        "day-one.xlsx",
    )

    next_day_timestamp = imported.snapshot_date + timedelta(
        days=1
    )

    next_day = replace(
        imported,
        snapshot_date=next_day_timestamp,
    )

    second = service.import_snapshot(
        "BMO",
        next_day,
        "day-two.xlsx",
    )

    assert first.duplicate is False
    assert second.duplicate is False
    assert second.replaced is False

    records = session.scalars(
        select(ImportRecord).order_by(
            ImportRecord.snapshot_date
        )
    ).all()

    assert len(records) == 2
    assert records[0].snapshot_day != records[1].snapshot_day

    account = _account(session, imported.account_number)

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

    assert len(holdings) == len(imported.holdings) * 2
    assert len(cash) == len(imported.cash) * 2


def test_import_preserves_brokerage_supplied_values(session):
    imported = _load_bmo()
    service = ImportService(session)

    service.import_snapshot(
        "BMO",
        imported,
        "values.xlsx",
    )

    account = _account(session, imported.account_number)

    source = imported.holdings[0]

    holding = session.scalar(
        select(HoldingSnapshot).where(
            HoldingSnapshot.account_id == account.id,
            HoldingSnapshot.company_id.is_not(None),
            HoldingSnapshot.snapshot_date
            == imported.snapshot_date,
        )
    )

    assert holding is not None
    assert holding.average_cost == source.average_cost
    assert holding.unrealized_gain == source.unrealized_gain
    assert (
        holding.unrealized_gain_percent
        == source.unrealized_gain_percent
    )
    assert holding.daily_change == source.daily_change
    assert (
        holding.daily_change_percent
        == source.daily_change_percent
    )
    assert holding.previous_close == source.previous_close
