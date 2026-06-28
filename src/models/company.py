"""
company.py

Defines the Company SQLAlchemy model.

A Company represents a unique publicly traded security.

Examples:
    - Royal Bank of Canada
    - Toronto-Dominion Bank
    - BCE Inc.
    - Apple Inc.

A Company exists only once in the database regardless of how many
accounts own the security.

Historical market prices and holding snapshots reference this entity.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.models.holding_snapshot import HoldingSnapshot
    from src.models.market_price import MarketPrice


class Company(Base):
    """
    Represents a publicly traded security.
    """

    __tablename__ = "companies"

    #
    # Primary Key
    #

    id: Mapped[int] = mapped_column(primary_key=True)

    #
    # Company Information
    #

    ticker: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    company_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    exchange: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    asset_class: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    sector: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    industry: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    #
    # Relationships
    #

    holding_snapshots: Mapped[list["HoldingSnapshot"]] = relationship(
        back_populates="company",
    )

    market_prices: Mapped[list["MarketPrice"]] = relationship(
        back_populates="company",
    )

    def __repr__(self) -> str:
        """
        Return a concise representation of the company.
        """
        return (
            f"Company("
            f"id={self.id}, "
            f"ticker='{self.ticker}', "
            f"name='{self.company_name}')"
        )