"""
test_company_repository.py

Unit tests for CompanyRepository.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.repositories.company_repository import CompanyRepository
from tests.entity_factory import create_company


def test_empty_repository(session: Session) -> None:
    """
    A newly created repository should contain no companies.
    """

    repository = CompanyRepository(session)

    assert repository.count() == 0

    assert repository.find_all() == []


def test_add_company(session: Session) -> None:
    """
    Verify a company can be persisted.
    """

    repository = CompanyRepository(session)

    company = create_company(session)

    session.commit()

    assert company.id is not None

    assert repository.count() == 1


def test_find_by_ticker(session: Session) -> None:
    """
    Verify a company can be found by ticker.
    """

    repository = CompanyRepository(session)

    company = create_company(session)

    session.commit()

    found = repository.find_by_ticker(
        company.ticker,
    )

    assert found is not None

    assert found.id == company.id


def test_find_by_ticker_case_insensitive(
    session: Session,
) -> None:
    """
    Verify ticker lookups ignore case.
    """

    repository = CompanyRepository(session)

    company = create_company(session)

    session.commit()

    assert repository.find_by_ticker(
        company.ticker.lower(),
    ) is not None

    assert repository.find_by_ticker(
        company.ticker.upper(),
    ) is not None


def test_find_all_returns_sorted(
    session: Session,
) -> None:
    """
    Verify companies are returned alphabetically.
    """

    repository = CompanyRepository(session)

    create_company(
        session,
        ticker="TD",
        company_name="Toronto-Dominion Bank",
    )

    create_company(
        session,
        ticker="BNS",
    )

    create_company(
        session,
        ticker="RY",
        company_name="Royal Bank of Canada",
    )

    session.commit()

    tickers = [
        company.ticker
        for company in repository.find_all()
    ]

    assert tickers == [
        "BNS",
        "RY",
        "TD",
    ]


def test_exists(session: Session) -> None:
    """
    Verify exists() behaves correctly.
    """

    repository = CompanyRepository(session)

    company = create_company(session)

    session.commit()

    assert repository.exists(
        company.ticker,
    )

    assert not repository.exists(
        "XYZ",
    )


def test_delete_company(
    session: Session,
) -> None:
    """
    Verify a company can be deleted.
    """

    repository = CompanyRepository(session)

    company = create_company(session)

    session.commit()

    repository.delete(company)

    session.commit()

    assert repository.count() == 0


def test_unknown_company_returns_none(
    session: Session,
) -> None:
    """
    Unknown tickers should return None.
    """

    repository = CompanyRepository(session)

    assert repository.find_by_ticker(
        "UNKNOWN",
    ) is None