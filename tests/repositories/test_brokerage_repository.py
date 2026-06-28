"""
test_brokerage_repository.py

Unit tests for BrokerageRepository.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.repositories.brokerage_repository import BrokerageRepository
from tests.entity_factory import create_brokerage


def test_empty_repository(session: Session) -> None:
    """
    A newly created repository should contain no brokerages.
    """

    repository = BrokerageRepository(session)

    assert repository.count() == 0
    assert repository.find_all() == []


def test_add_brokerage(session: Session) -> None:
    """
    Verify a brokerage can be persisted.
    """

    repository = BrokerageRepository(session)

    brokerage = create_brokerage(session)

    session.commit()

    assert brokerage.id is not None
    assert repository.count() == 1


def test_find_by_id(session: Session) -> None:
    """
    Verify brokerages can be found by primary key.
    """

    repository = BrokerageRepository(session)

    brokerage = create_brokerage(session)

    session.commit()

    found = repository.find_by_id(brokerage.id)

    assert found is not None
    assert found.name == brokerage.name


def test_find_by_name(session: Session) -> None:
    """
    Verify brokerages can be found by name.
    """

    repository = BrokerageRepository(session)

    brokerage = create_brokerage(session)

    session.commit()

    found = repository.find_by_name(
        brokerage.name,
    )

    assert found is not None
    assert found.id == brokerage.id


def test_find_all_returns_sorted_names(
    session: Session,
) -> None:
    """
    Verify brokerages are returned alphabetically.
    """

    repository = BrokerageRepository(session)

    create_brokerage(
        session,
        name="TD Direct Investing",
    )

    create_brokerage(
        session,
        name="BMO InvestorLine",
    )

    create_brokerage(
        session,
        name="RBC Direct Investing",
    )

    session.commit()

    names = [
        brokerage.name
        for brokerage in repository.find_all()
    ]

    assert names == [
        "BMO InvestorLine",
        "RBC Direct Investing",
        "TD Direct Investing",
    ]


def test_exists(session: Session) -> None:
    """
    Verify exists() behaves correctly.
    """

    repository = BrokerageRepository(session)

    brokerage = create_brokerage(session)

    session.commit()

    assert repository.exists(
        brokerage.name,
    )

    assert not repository.exists(
        "Scotia iTRADE",
    )


def test_delete(session: Session) -> None:
    """
    Verify a brokerage can be deleted.
    """

    repository = BrokerageRepository(session)

    brokerage = create_brokerage(session)

    session.commit()

    repository.delete(brokerage)

    session.commit()

    assert repository.count() == 0


def test_find_unknown_returns_none(
    session: Session,
) -> None:
    """
    Unknown brokerages should return None.
    """

    repository = BrokerageRepository(session)

    assert repository.find_by_name(
        "Unknown",
    ) is None

    assert repository.find_by_id(
        9999,
    ) is None