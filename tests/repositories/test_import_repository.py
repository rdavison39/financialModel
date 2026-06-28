"""
test_import_repository.py

Unit tests for ImportRepository.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.repositories.import_repository import ImportRepository
from tests.entity_factory import (
    create_brokerage,
    create_import,
)


def test_empty_repository(session: Session) -> None:
    """
    A newly created repository should contain no imports.
    """

    repository = ImportRepository(session)

    assert repository.count() == 0

    assert repository.find_all() == []


def test_add_import(session: Session) -> None:
    """
    Verify an import record can be persisted.
    """

    brokerage = create_brokerage(session)

    repository = ImportRepository(session)

    record = create_import(
        session,
        brokerage,
    )

    session.commit()

    assert record.id is not None

    assert repository.count() == 1


def test_find_by_id(session: Session) -> None:
    """
    Verify an import record can be found by ID.
    """

    brokerage = create_brokerage(session)

    repository = ImportRepository(session)

    record = create_import(
        session,
        brokerage,
    )

    session.commit()

    found = repository.find_by_id(
        record.id,
    )

    assert found is not None

    assert found.id == record.id


def test_find_by_brokerage(
    session: Session,
) -> None:
    """
    Verify imports can be retrieved for a brokerage.
    """

    brokerage = create_brokerage(session)

    repository = ImportRepository(session)

    create_import(
        session,
        brokerage,
    )

    create_import(
        session,
        brokerage,
        source_folder="c:/imports2",
    )

    session.commit()

    imports = repository.find_by_brokerage(
        brokerage.id,
    )

    assert len(imports) == 2


def test_find_latest(
    session: Session,
) -> None:
    """
    Verify the latest import is returned.
    """

    brokerage = create_brokerage(session)

    repository = ImportRepository(session)

    create_import(
        session,
        brokerage,
        source_folder="c:/imports1",
    )

    latest = create_import(
        session,
        brokerage,
        source_folder="c:/imports2",
    )

    session.commit()

    found = repository.find_latest()

    assert found is not None

    assert found.id == latest.id


def test_latest_for_brokerage(
    session: Session,
) -> None:
    """
    Verify latest_for_brokerage() returns the latest import.
    """

    brokerage = create_brokerage(session)

    repository = ImportRepository(session)

    create_import(
        session,
        brokerage,
        source_folder="c:/imports1",
    )

    latest = create_import(
        session,
        brokerage,
        source_folder="c:/imports2",
    )

    session.commit()

    found = repository.latest_for_brokerage(
        brokerage.id,
    )

    assert found is not None

    assert found.id == latest.id


def test_delete_import(
    session: Session,
) -> None:
    """
    Verify an import record can be deleted.
    """

    brokerage = create_brokerage(session)

    repository = ImportRepository(session)

    record = create_import(
        session,
        brokerage,
    )

    session.commit()

    repository.delete(record)

    session.commit()

    assert repository.count() == 0


def test_unknown_import_returns_none(
    session: Session,
) -> None:
    """
    Unknown imports should return None.
    """

    repository = ImportRepository(session)

    assert repository.find_by_id(
        999999,
    ) is None