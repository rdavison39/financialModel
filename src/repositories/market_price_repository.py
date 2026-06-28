"""
market_price_repository.py

Repository for MarketPrice entities.

Repositories encapsulate all database access for MarketPrice
entities.

Business logic does not belong in repositories.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import select

from src.models.market_price import MarketPrice
from src.repositories.repository_base import RepositoryBase


class MarketPriceRepository(RepositoryBase[MarketPrice]):
    """
    Repository for MarketPrice entities.
    """

    def find_by_id(
        self,
        market_price_id: int,
    ) -> MarketPrice | None:
        """
        Find a market price by its primary key.
        """

        statement = (
            select(MarketPrice)
            .where(MarketPrice.id == market_price_id)
        )

        return self._scalar(statement)

    def find_price(
        self,
        company_id: int,
        price_date: date,
    ) -> MarketPrice | None:
        """
        Return the market price for a company on a specific date.
        """

        statement = (
            select(MarketPrice)
            .where(MarketPrice.company_id == company_id)
            .where(MarketPrice.price_date == price_date)
        )

        return self._scalar(statement)

    def find_latest_price(
        self,
        company_id: int,
    ) -> MarketPrice | None:
        """
        Return the most recent market price for a company.
        """

        statement = (
            select(MarketPrice)
            .where(MarketPrice.company_id == company_id)
            .order_by(desc(MarketPrice.price_date))
            .limit(1)
        )

        return self._scalar(statement)

    def find_by_company(
        self,
        company_id: int,
    ) -> list[MarketPrice]:
        """
        Return all market prices for a company ordered by date.
        """

        statement = (
            select(MarketPrice)
            .where(MarketPrice.company_id == company_id)
            .order_by(MarketPrice.price_date)
        )

        return self._list(statement)

    def find_between_dates(
        self,
        company_id: int,
        start_date: date,
        end_date: date,
    ) -> list[MarketPrice]:
        """
        Return market prices within the specified date range.
        """

        statement = (
            select(MarketPrice)
            .where(MarketPrice.company_id == company_id)
            .where(MarketPrice.price_date >= start_date)
            .where(MarketPrice.price_date <= end_date)
            .order_by(MarketPrice.price_date)
        )

        return self._list(statement)

    def exists(
        self,
        company_id: int,
        price_date: date,
    ) -> bool:
        """
        Determine whether a market price exists.
        """

        return (
            self.find_price(
                company_id,
                price_date,
            )
            is not None
        )

    def count(self) -> int:
        """
        Return the total number of market prices.
        """

        statement = select(func.count(MarketPrice.id))

        result = self.session.scalar(statement)

        return 0 if result is None else int(result)

    def count_for_company(
        self,
        company_id: int,
    ) -> int:
        """
        Return the number of market prices for a company.
        """

        statement = (
            select(func.count(MarketPrice.id))
            .where(MarketPrice.company_id == company_id)
        )

        result = self.session.scalar(statement)

        return 0 if result is None else int(result)