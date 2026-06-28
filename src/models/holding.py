"""
holding.py

Defines the Holding model.

A Holding represents one company's position inside one account.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from src.database.base import Base


class Holding(Base):
    """
    Represents one security held in one account.
    """

    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
        index=True,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    shares: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    average_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    book_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    market_price: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    market_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    unrealized_gain: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    import_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    #
    # Relationships
    #

    account = relationship(
        "Account",
        back_populates="holdings",
    )

    company = relationship(
        "Company",
        back_populates="holdings",
    )

    def __repr__(self) -> str:

        return (
            f"Holding("
            f"{self.company.ticker}, "
            f"{self.shares} shares)"
        )