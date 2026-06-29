"""
Unit tests for CashBalanceSnapshotRepository.
"""

from __future__ import annotations

from decimal import Decimal

from src.repositories.cash_balance_snapshot_repository import (
    CashBalanceSnapshotRepository,
)
from tests.entity_factory import (
    create_account,
    create_brokerage,
    create_cash_balance_snapshot,
    create_import,
)


def test_find_by_id(
    session,
) -> None:

    brokerage = create_brokerage(session)

    account = create_account(
        session,
        brokerage,
    )

    import_record = create_import(
        session,
        brokerage,
    )

    snapshot = create_cash_balance_snapshot(
        session,
        import_record,
        account,
    )

    repository = CashBalanceSnapshotRepository(session)

    found = repository.find_by_id(snapshot.id)

    assert found == snapshot


def test_find_by_import(
    session,
) -> None:

    brokerage = create_brokerage(session)

    account = create_account(
        session,
        brokerage,
    )

    import_record = create_import(
        session,
        brokerage,
    )

    create_cash_balance_snapshot(
        session,
        import_record,
        account,
        currency="CAD",
    )

    create_cash_balance_snapshot(
        session,
        import_record,
        account,
        currency="USD",
    )

    repository = CashBalanceSnapshotRepository(session)

    snapshots = repository.find_by_import(
        import_record.id,
    )

    assert len(snapshots) == 2


def test_find_by_account(
    session,
) -> None:

    brokerage = create_brokerage(session)

    account = create_account(
        session,
        brokerage,
    )

    import_record = create_import(
        session,
        brokerage,
    )

    create_cash_balance_snapshot(
        session,
        import_record,
        account,
        currency="CAD",
    )

    create_cash_balance_snapshot(
        session,
        import_record,
        account,
        currency="USD",
    )

    repository = CashBalanceSnapshotRepository(session)

    snapshots = repository.find_by_account(
        account.id,
    )

    assert len(snapshots) == 2


def test_find_by_account_and_currency(
    session,
) -> None:

    brokerage = create_brokerage(session)

    account = create_account(
        session,
        brokerage,
    )

    import_record = create_import(
        session,
        brokerage,
    )

    create_cash_balance_snapshot(
        session,
        import_record,
        account,
        currency="CAD",
    )

    usd = create_cash_balance_snapshot(
        session,
        import_record,
        account,
        currency="USD",
    )

    repository = CashBalanceSnapshotRepository(session)

    found = repository.find_by_account_and_currency(
        account.id,
        "USD",
    )

    assert found == usd


def test_find_latest_for_account(
    session,
) -> None:

    brokerage = create_brokerage(session)

    account = create_account(
        session,
        brokerage,
    )

    import_record = create_import(
        session,
        brokerage,
    )

    create_cash_balance_snapshot(
        session,
        import_record,
        account,
        currency="CAD",
    )

    repository = CashBalanceSnapshotRepository(session)

    snapshots = repository.find_latest_for_account(
        account.id,
        import_record.id,
    )

    assert len(snapshots) == 1


def test_find_latest_portfolio(
    session,
) -> None:

    brokerage = create_brokerage(session)

    account = create_account(
        session,
        brokerage,
    )

    import_record = create_import(
        session,
        brokerage,
    )

    create_cash_balance_snapshot(
        session,
        import_record,
        account,
        currency="CAD",
    )

    repository = CashBalanceSnapshotRepository(session)

    snapshots = repository.find_latest_portfolio(
        import_record.id,
    )

    assert len(snapshots) == 1


def test_count(
    session,
) -> None:

    brokerage = create_brokerage(session)

    account = create_account(
        session,
        brokerage,
    )

    import_record = create_import(
        session,
        brokerage,
    )

    create_cash_balance_snapshot(
        session,
        import_record,
        account,
    )

    repository = CashBalanceSnapshotRepository(session)

    assert repository.count() == 1


def test_count_for_import(
    session,
) -> None:

    brokerage = create_brokerage(session)

    account = create_account(
        session,
        brokerage,
    )

    import_record = create_import(
        session,
        brokerage,
    )

    create_cash_balance_snapshot(
        session,
        import_record,
        account,
        currency="CAD",
    )

    create_cash_balance_snapshot(
        session,
        import_record,
        account,
        currency="USD",
    )

    repository = CashBalanceSnapshotRepository(session)

    assert (
        repository.count_for_import(
            import_record.id,
        )
        == 2
    )


def test_find_by_account_and_currency_returns_none(
    session,
) -> None:

    brokerage = create_brokerage(session)

    account = create_account(
        session,
        brokerage,
    )

    repository = CashBalanceSnapshotRepository(session)

    found = repository.find_by_account_and_currency(
        account.id,
        "CAD",
    )

    assert found is None