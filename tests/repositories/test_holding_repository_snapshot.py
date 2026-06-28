"""
test_holding_snapshot_repository.py

Unit tests for HoldingSnapshotRepository.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.repositories.holding_snapshot_repository import (
    HoldingSnapshotRepository,
)
from tests.entity_factory import (
    create_account,
    create_brokerage,
    create_company,
    create_holding_snapshot,
    create_import,
)


def test_empty_repository(session: Session) -> None:
    """
    A newly created repository should contain no holdings.
    """

    repository = HoldingSnapshotRepository(session)

    assert repository.count() == 0

    assert repository.find_all() == []


def test_add_holding(session: Session) -> None:
    """
    Verify a holding snapshot can be persisted.
    """

    brokerage = create_brokerage(session)
    account = create_account(session, brokerage)
    company = create_company(session)
    import_record = create_import(session, brokerage)

    repository = HoldingSnapshotRepository(session)

    holding = create_holding_snapshot(
        session,
        import_record,
        account,
        company,
    )

    session.commit()

    assert holding.id is not None

    assert repository.count() == 1


def test_find_by_import(session: Session) -> None:
    """
    Verify holdings can be found by import.
    """

    brokerage = create_brokerage(session)
    account = create_account(session, brokerage)
    company = create_company(session)
    import_record = create_import(session, brokerage)

    repository = HoldingSnapshotRepository(session)

    create_holding_snapshot(
        session,
        import_record,
        account,
        company,
    )

    session.commit()

    holdings = repository.find_by_import(
        import_record.id,
    )

    assert len(holdings) == 1


def test_find_by_account(session: Session) -> None:
    """
    Verify holdings can be found by account.
    """

    brokerage = create_brokerage(session)
    account = create_account(session, brokerage)
    company = create_company(session)
    import_record = create_import(session, brokerage)

    repository = HoldingSnapshotRepository(session)

    create_holding_snapshot(
        session,
        import_record,
        account,
        company,
    )

    session.commit()

    holdings = repository.find_by_account(
        account.id,
    )

    assert len(holdings) == 1


def test_find_by_company(session: Session) -> None:
    """
    Verify holdings can be found by company.
    """

    brokerage = create_brokerage(session)
    account = create_account(session, brokerage)
    company = create_company(session)
    import_record = create_import(session, brokerage)

    repository = HoldingSnapshotRepository(session)

    create_holding_snapshot(
        session,
        import_record,
        account,
        company,
    )

    session.commit()

    holdings = repository.find_by_company(
        company.id,
    )

    assert len(holdings) == 1


def test_count_for_import(session: Session) -> None:
    """
    Verify count_for_import() returns the correct value.
    """

    brokerage = create_brokerage(session)
    account = create_account(session, brokerage)
    company = create_company(session)
    import_record = create_import(session, brokerage)

    repository = HoldingSnapshotRepository(session)

    create_holding_snapshot(
        session,
        import_record,
        account,
        company,
    )

    session.commit()

    assert repository.count_for_import(
        import_record.id,
    ) == 1


def test_delete_holding(session: Session) -> None:
    """
    Verify a holding snapshot can be deleted.
    """

    brokerage = create_brokerage(session)
    account = create_account(session, brokerage)
    company = create_company(session)
    import_record = create_import(session, brokerage)

    repository = HoldingSnapshotRepository(session)

    holding = create_holding_snapshot(
        session,
        import_record,
        account,
        company,
    )

    session.commit()

    repository.delete(holding)

    session.commit()

    assert repository.count() == 0


def test_unknown_import_returns_empty_list(
    session: Session,
) -> None:
    """
    Unknown imports should return an empty list.
    """

    repository = HoldingSnapshotRepository(session)

    assert repository.find_by_import(
        999999,
    ) == []