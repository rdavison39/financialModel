"""
market_price.py

Defines the MarketPrice SQLAlchemy model.

A MarketPrice represents the historical market price of a security
for a single trading day.

Market prices are immutable and provide the foundation for
historical portfolio valuation, performance analysis, dividend
tracking, and future retirement modelling.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Numeric
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.models.company import Company


class MarketPrice(Base):
    """
    Represents the historical market price of a security for one
    trading day.
    """

    __tablename__ = "market_prices"

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "price_date",
            name="uq_market_prices_company_date",
        ),
    )

    #
    # Primary Key
    #

    id: Mapped[int] = mapped_column(primary_key=True)

    #
    # Foreign Key
    #

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    #
    # Price Information
    #

    price_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    open: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    high: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    low: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    close: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    volume: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    dividend: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
        default=Decimal("0"),
    )

    #
    # Relationships
    #

    company: Mapped["Company"] = relationship(
        back_populates="market_prices",
    )

    def __repr__(self) -> str:
        """
        Return a concise representation of the market price.
        """
        return (
            f"MarketPrice("
            f"id={self.id}, "
            f"company_id={self.company_id}, "
            f"date={self.price_date}, "
            f"close={self.close})"
        )