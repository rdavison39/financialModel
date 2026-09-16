"""
Service for managing companies and securities.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.company import Company


class CompanyService:
    """Manages companies and securities."""

    def __init__(self, session: Session) -> None:
        """Initialize the company service."""
        self.session = session

    def get_or_create(
        self,
        symbol: str,
        name: str,
    ) -> Company:
        """
        Find a company by symbol or create it if it does not exist.
        """

        company = self.session.scalar(
            select(Company).where(
                Company.symbol == symbol,
            )
        )

        if company is not None:
            return company

        company = Company(
            symbol=symbol,
            name=name,
        )

        self.session.add(company)
        self.session.commit()
        self.session.refresh(company)

        return company

    def get(self, company_id: int) -> Company | None:
        """Return a company by ID."""

        return self.session.get(Company, company_id)

    def get_by_symbol(self, symbol: str) -> Company | None:
        """Return a company by ticker symbol."""

        return self.session.scalar(
            select(Company).where(
                Company.symbol == symbol,
            )
        )

    def get_all(self) -> list[Company]:
        """Return all companies ordered by symbol."""

        return list(
            self.session.scalars(
                select(Company).order_by(Company.symbol)
            ).all()
        )