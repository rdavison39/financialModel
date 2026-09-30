from datetime import date
from decimal import Decimal

import pytest

from src.models.account import Account
from src.models.brokerage import Brokerage
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.services.snapshot_management_service import SnapshotManagementService


def test_get_snapshots_keeps_latest_row_when_same_date_exists(session):
    brokerage = Brokerage(name="BMO")
    session.add(brokerage)
    session.flush()
    account = Account(
        brokerage_id=brokerage.id,
        account_number="123",
        name="RRSP",
    )
    session.add(account)
    session.flush()

    first = PortfolioSnapshot(
        account_id=account.id,
        snapshot_date=date(2026, 9, 29),
        total_value=Decimal("100000"),
    )
    latest = PortfolioSnapshot(
        account_id=account.id,
        snapshot_date=date(2026, 9, 29),
        total_value=Decimal("101000"),
    )
    older = PortfolioSnapshot(
        account_id=account.id,
        snapshot_date=date(2026, 9, 28),
        total_value=Decimal("99000"),
    )
    session.add_all([first, latest, older])
    session.commit()

    rows = SnapshotManagementService(session).get_snapshots(account.id)

    assert [row.snapshot_date for row in rows] == [date(2026, 9, 29), date(2026, 9, 28)]
    assert rows[0].total_value == Decimal("101000")


def test_update_cash_flow_validates_and_persists(session):
    brokerage = Brokerage(name="NB")
    session.add(brokerage)
    session.flush()
    account = Account(
        brokerage_id=brokerage.id,
        account_number="456",
        name="RRSP",
    )
    session.add(account)
    session.flush()
    snapshot = PortfolioSnapshot(
        account_id=account.id,
        snapshot_date=date(2026, 9, 29),
        total_value=Decimal("200000"),
    )
    session.add(snapshot)
    session.commit()

    SnapshotManagementService(session).update_cash_flow(
        snapshot.id,
        "10000",
        "250.50",
    )

    session.refresh(snapshot)
    assert snapshot.external_added == Decimal("10000.00")
    assert snapshot.external_withdrawn == Decimal("250.50")

    with pytest.raises(ValueError, match="cannot be negative"):
        SnapshotManagementService(session).update_cash_flow(snapshot.id, "-1", "0")
