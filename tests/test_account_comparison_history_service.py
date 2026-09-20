"""Tests for the multi-account comparison history service."""

from datetime import date
from decimal import Decimal

from src.models.account import Account
from src.models.brokerage import Brokerage
from sqlalchemy import select
from src.models.portfolio_snapshot import PortfolioSnapshot
from src.services.account_comparison_history_service import (
    AccountComparisonHistoryService,
)


def add_account(session, brokerage_name, account_number, name):
    """Create and persist a brokerage/account pair."""
    brokerage = session.scalar(
        select(Brokerage).where(Brokerage.name == brokerage_name)
    )
    if brokerage is None:
        brokerage = Brokerage(name=brokerage_name)
        session.add(brokerage)
        session.flush()

    account = Account(
        brokerage_id=brokerage.id,
        account_number=account_number,
        name=name,
    )
    session.add(account)
    session.flush()
    return account


def add_snapshot(session, account_id, snapshot_date, value):
    """Create an account portfolio snapshot."""
    snapshot = PortfolioSnapshot(
        account_id=account_id,
        snapshot_date=snapshot_date,
        total_value=Decimal(value),
    )
    session.add(snapshot)
    session.flush()
    return snapshot


def test_get_accounts_returns_brokerage_account_and_name(session):
    """Accounts are returned with the identity information needed by the UI."""
    account = add_account(session, "BMO", "12345", "Ron RRSP")

    result = AccountComparisonHistoryService(session).get_accounts()

    assert len(result) == 1
    assert result[0].account_id == account.id
    assert result[0].brokerage_name == "BMO"
    assert result[0].account_number == "12345"
    assert result[0].account_name == "Ron RRSP"
    assert result[0].label == "BMO - 12345 - Ron RRSP"


def test_get_accounts_orders_by_brokerage_then_account_number(session):
    """Account ordering is stable and matches the comparison selector."""
    add_account(session, "NB", "900", "NB 900")
    add_account(session, "BMO", "200", "BMO 200")
    add_account(session, "BMO", "100", "BMO 100")

    result = AccountComparisonHistoryService(session).get_accounts()

    assert [(item.brokerage_name, item.account_number) for item in result] == [
        ("BMO", "100"),
        ("BMO", "200"),
        ("NB", "900"),
    ]


def test_get_histories_returns_only_selected_accounts(session):
    """Unselected accounts never appear in comparison history."""
    first = add_account(session, "BMO", "1", "First")
    second = add_account(session, "BMO", "2", "Second")
    add_snapshot(session, first.id, date(2026, 9, 17), "100000")
    add_snapshot(session, second.id, date(2026, 9, 17), "200000")

    result = AccountComparisonHistoryService(session).get_histories(
        [first.id],
        date(2026, 9, 1),
        date(2026, 9, 30),
    )

    assert set(result) == {first.id}
    assert result[first.id][0].total_value == Decimal("100000.00")


def test_get_histories_deduplicates_account_ids(session):
    """Duplicate selections do not duplicate graph points."""
    account = add_account(session, "BMO", "1", "First")
    add_snapshot(session, account.id, date(2026, 9, 17), "100000")

    result = AccountComparisonHistoryService(session).get_histories(
        [account.id, account.id, account.id],
        date(2026, 9, 1),
        date(2026, 9, 30),
    )

    assert len(result[account.id]) == 1


def test_get_histories_respects_date_range(session):
    """Only snapshots inside the requested date range are returned."""
    account = add_account(session, "BMO", "1", "First")
    add_snapshot(session, account.id, date(2026, 9, 10), "100000")
    add_snapshot(session, account.id, date(2026, 9, 17), "110000")
    add_snapshot(session, account.id, date(2026, 9, 20), "120000")

    result = AccountComparisonHistoryService(session).get_histories(
        [account.id],
        date(2026, 9, 17),
        date(2026, 9, 19),
    )

    assert [point.snapshot_date for point in result[account.id]] == [
        date(2026, 9, 17)
    ]


def test_get_histories_orders_points_by_date(session):
    """History points are returned chronologically."""
    account = add_account(session, "BMO", "1", "First")
    add_snapshot(session, account.id, date(2026, 9, 19), "120000")
    add_snapshot(session, account.id, date(2026, 9, 17), "100000")
    add_snapshot(session, account.id, date(2026, 9, 18), "110000")

    result = AccountComparisonHistoryService(session).get_histories(
        [account.id],
        date(2026, 9, 17),
        date(2026, 9, 19),
    )

    assert [point.snapshot_date for point in result[account.id]] == [
        date(2026, 9, 17),
        date(2026, 9, 18),
        date(2026, 9, 19),
    ]
    assert [point.total_value for point in result[account.id]] == [
        Decimal("100000.00"),
        Decimal("110000.00"),
        Decimal("120000.00"),
    ]


def test_get_histories_ignores_consolidated_snapshots(session):
    """The comparison screen uses individual accounts, never account_id=None."""
    account = add_account(session, "BMO", "1", "First")
    add_snapshot(session, None, date(2026, 9, 17), "999999")
    add_snapshot(session, account.id, date(2026, 9, 17), "100000")

    result = AccountComparisonHistoryService(session).get_histories(
        [account.id],
        date(2026, 9, 17),
        date(2026, 9, 17),
    )

    assert result[account.id][0].total_value == Decimal("100000.00")


def test_get_histories_returns_empty_for_no_accounts(session):
    """No selection produces no history."""
    result = AccountComparisonHistoryService(session).get_histories(
        [],
        date(2026, 9, 1),
        date(2026, 9, 30),
    )

    assert result == {}


def test_get_histories_returns_empty_for_invalid_date_range(session):
    """An inverted date range produces no history."""
    account = add_account(session, "BMO", "1", "First")
    add_snapshot(session, account.id, date(2026, 9, 17), "100000")

    result = AccountComparisonHistoryService(session).get_histories(
        [account.id],
        date(2026, 9, 30),
        date(2026, 9, 1),
    )

    assert result == {}
