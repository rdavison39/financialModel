"""
test_market_price_repository.py

Unit tests for MarketPriceRepository.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.repositories.market_price_repository import (
    MarketPriceRepository,
)
from tests.entity_factory import (
    create_company,
    create_market_price,
)


def test_empty_repository(session: Session) -> None:
    """
    A newly created repository should contain no market prices.
    """

    repository = MarketPriceRepository(session)

    assert repository.count() == 0

    assert repository.find_by_company(1) == []


def test_add_market_price(session: Session) -> None:
    """
    Verify a market price can be persisted.
    """

    company = create_company(session)

    repository = MarketPriceRepository(session)

    price = create_market_price(
        session,
        company,
    )

    session.commit()

    assert price.id is not None

    assert repository.count() == 1


def test_find_price(session: Session) -> None:
    """
    Verify a market price can be found.
    """

    company = create_company(session)

    repository = MarketPriceRepository(session)

    create_market_price(
        session,
        company,
        price_date=date(2026, 6, 30),
        close=Decimal("55.10"),
    )

    session.commit()

    found = repository.find_price(
        company.id,
        date(2026, 6, 30),
    )

    assert found is not None

    assert found.close == Decimal("55.10")


def test_find_latest_price(session: Session) -> None:
    """
    Verify the latest market price is returned.
    """

    company = create_company(session)

    repository = MarketPriceRepository(session)

    create_market_price(
        session,
        company,
        price_date=date(2026, 6, 29),
        close=Decimal("54.00"),
    )

    latest = create_market_price(
        session,
        company,
        price_date=date(2026, 6, 30),
        close=Decimal("55.10"),
    )

    session.commit()

    found = repository.find_latest_price(
        company.id,
    )

    assert found is not None

    assert found.id == latest.id

    assert found.close == Decimal("55.10")


def test_find_between_dates(
    session: Session,
) -> None:
    """
    Verify prices can be retrieved within a date range.
    """

    company = create_company(session)

    repository = MarketPriceRepository(session)

    create_market_price(
        session,
        company,
        price_date=date(2026, 6, 28),
    )

    create_market_price(
        session,
        company,
        price_date=date(2026, 6, 29),
    )

    create_market_price(
        session,
        company,
        price_date=date(2026, 6, 30),
    )

    session.commit()

    prices = repository.find_between_dates(
        company.id,
        date(2026, 6, 29),
        date(2026, 6, 30),
    )

    assert len(prices) == 2


def test_exists(session: Session) -> None:
    """
    Verify exists() behaves correctly.
    """

    company = create_company(session)

    repository = MarketPriceRepository(session)

    create_market_price(
        session,
        company,
    )

    session.commit()

    assert repository.exists(
        company.id,
        date(2026, 6, 30),
    )

    assert not repository.exists(
        company.id,
        date(2026, 7, 1),
    )


def test_count_for_company(
    session: Session,
) -> None:
    """
    Verify count_for_company() returns the correct value.
    """

    company = create_company(session)

    repository = MarketPriceRepository(session)

    create_market_price(
        session,
        company,
        price_date=date(2026, 6, 29),
    )

    create_market_price(
        session,
        company,
        price_date=date(2026, 6, 30),
    )

    session.commit()

    assert repository.count_for_company(
        company.id,
    ) == 2


def test_delete_market_price(
    session: Session,
) -> None:
    """
    Verify a market price can be deleted.
    """

    company = create_company(session)

    repository = MarketPriceRepository(session)

    price = create_market_price(
        session,
        company,
    )

    session.commit()

    repository.delete(price)

    session.commit()

    assert repository.count() == 0


def test_unknown_price_returns_none(
    session: Session,
) -> None:
    """
    Unknown prices should return None.
    """

    repository = MarketPriceRepository(session)

    assert repository.find_price(
        999999,
        date(2026, 6, 30),
    ) is None