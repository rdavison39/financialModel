"""
company_repository.py

Repository for Company entities.

Repositories encapsulate all database access for Company entities.

Business logic does not belong in repositories.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy import select

from src.models.company import Company
from src.repositories.repository_base import RepositoryBase


class CompanyRepository(RepositoryBase[Company]):
    """
    Repository for Company entities.
    """

    def find_by_id(
        self,
        company_id: int,
    ) -> Company | None:
        """
        Find a company by its primary key.
        """

        statement = (
            select(Company)
            .where(Company.id == company_id)
        )

        return self._scalar(statement)

    def find_by_ticker(
        self,
        ticker: str,
    ) -> Company | None:
        """
        Find a company by ticker symbol.
        """

        statement = (
            select(Company)
            .where(Company.ticker == ticker.upper())
        )

        return self._scalar(statement)

    def find_all(self) -> list[Company]:
        """
        Return all companies ordered by ticker.
        """

        statement = (
            select(Company)
            .order_by(Company.ticker)
        )

        return self._list(statement)

    def exists(
        self,
        ticker: str,
    ) -> bool:
        """
        Determine whether a company exists.
        """

        return self.find_by_ticker(ticker) is not None

    def count(self) -> int:
        """
        Return the number of companies.

        Uses SQL COUNT(*) rather than loading every row.
        """

        statement = select(func.count(Company.id))

        result = self.session.scalar(statement)

        return 0 if result is None else int(result)

    def create_if_missing(
        self,
        *,
        ticker: str,
        company_name: str,
        exchange: str,
        currency: str,
        asset_class: str,
        sector: str,
        industry: str,
        country: str,
    ) -> Company:
        """
        Return an existing company or create a new one.

        The company is added to the current session but is not
        committed. The caller is responsible for committing the
        transaction.
        """

        company = self.find_by_ticker(ticker)

        if company is not None:
            return company

        company = Company(
            ticker=ticker.upper(),
            company_name=company_name,
            exchange=exchange,
            currency=currency,
            asset_class=asset_class,
            sector=sector,
            industry=industry,
            country=country,
            active=True,
        )

        self.add(company)

        return company