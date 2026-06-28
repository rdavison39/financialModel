"""
test_account_repository.py

Unit tests for AccountRepository.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.repositories.account_repository import AccountRepository
from tests.entity_factory import (
    create_account,
    create_brokerage,
)


def test_empty_repository(session: Session) -> None:
    """
    A newly created repository should contain no accounts.
    """

    repository = AccountRepository(session)

    assert repository.count() == 0

    assert repository.find_all() == []


def test_add_account(session: Session) -> None:
    """
    Verify an account can be persisted.
    """

    brokerage = create_brokerage(session)

    repository = AccountRepository(session)

    account = create_account(
        session,
        brokerage,
    )

    session.commit()

    assert account.id is not None

    assert repository.count() == 1


def test_find_by_account_number(
    session: Session,
) -> None:
    """
    Verify an account can be found by brokerage and account number.
    """

    brokerage = create_brokerage(session)

    repository = AccountRepository(session)

    account = create_account(
        session,
        brokerage,
    )

    session.commit()

    found = repository.find_by_account_number(
        brokerage.id,
        account.account_number,
    )

    assert found is not None

    assert found.id == account.id


def test_find_by_owner(
    session: Session,
) -> None:
    """
    Verify accounts can be retrieved by owner.
    """

    brokerage = create_brokerage(session)

    repository = AccountRepository(session)

    create_account(
        session,
        brokerage,
        account_number="11111111",
        account_name="RRSP",
    )

    create_account(
        session,
        brokerage,
        account_number="22222222",
        account_name="TFSA",
    )

    session.commit()

    accounts = repository.find_by_owner(
        "Ron Davison",
    )

    assert len(accounts) == 2


def test_exists(session: Session) -> None:
    """
    Verify exists() behaves correctly.
    """

    brokerage = create_brokerage(session)

    repository = AccountRepository(session)

    account = create_account(
        session,
        brokerage,
    )

    session.commit()

    assert repository.exists(
        brokerage.id,
        account.account_number,
    )

    assert not repository.exists(
        brokerage.id,
        "99999999",
    )


def test_find_all_returns_sorted_accounts(
    session: Session,
) -> None:
    """
    Verify accounts are returned in account name order.
    """

    brokerage = create_brokerage(session)

    repository = AccountRepository(session)

    create_account(
        session,
        brokerage,
        account_name="TFSA",
        account_number="22222222",
    )

    create_account(
        session,
        brokerage,
        account_name="Cash",
        account_number="33333333",
    )

    create_account(
        session,
        brokerage,
        account_name="RRSP",
        account_number="11111111",
    )

    session.commit()

    names = [
        account.account_name
        for account in repository.find_all()
    ]

    assert names == [
        "Cash",
        "RRSP",
        "TFSA",
    ]


def test_delete_account(
    session: Session,
) -> None:
    """
    Verify an account can be deleted.
    """

    brokerage = create_brokerage(session)

    repository = AccountRepository(session)

    account = create_account(
        session,
        brokerage,
    )

    session.commit()

    repository.delete(account)

    session.commit()

    assert repository.count() == 0


def test_unknown_account_returns_none(
    session: Session,
) -> None:
    """
    Unknown account numbers should return None.
    """

    brokerage = create_brokerage(session)

    repository = AccountRepository(session)

    assert repository.find_by_account_number(
        brokerage.id,
        "99999999",
    ) is None