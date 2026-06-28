"""
brokerage.py

Defines the Brokerage SQLAlchemy model.

A Brokerage represents a financial institution that provides
investment accounts and brokerage exports.

Examples:
    - BMO InvestorLine
    - RBC Direct Investing
    - Questrade
    - Interactive Brokers

A Brokerage is relatively static and serves as the parent entity
for investment accounts and brokerage imports.

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
    from src.models.account import Account
    from src.models.import_record import Import


class Brokerage(Base):
    """
    Represents a brokerage firm.

    A brokerage owns one or more investment accounts and is associated
    with one or more brokerage import operations.
    """

    __tablename__ = "brokerages"

    #
    # Primary Key
    #

    id: Mapped[int] = mapped_column(primary_key=True)

    #
    # Brokerage Information
    #

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    importer: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    website: Mapped[str] = mapped_column(
        String(255),
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

    accounts: Mapped[list["Account"]] = relationship(
        back_populates="brokerage",
    )

    imports: Mapped[list["Import"]] = relationship(
        back_populates="brokerage",
    )

    def __repr__(self) -> str:
        """
        Return a concise representation of the brokerage.
        """
        return (
            f"Brokerage("
            f"id={self.id}, "
            f"name='{self.name}')"
        )