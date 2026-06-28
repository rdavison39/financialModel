"""
account.py

Defines the Account SQLAlchemy model.

An Account represents a single investment account held at a brokerage.

Examples:
    - Ron RRSP
    - Ron TFSA
    - Ron Margin
    - Sonya RRSP
    - Family Trust

An Account is relatively static and is referenced by every
HoldingSnapshot imported from brokerage exports.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.models.brokerage import Brokerage
    from src.models.holding_snapshot import HoldingSnapshot


class Account(Base):
    """
    Represents one investment account.
    """

    __tablename__ = "accounts"

    __table_args__ = (
        UniqueConstraint(
            "brokerage_id",
            "account_number",
            name="uq_accounts_brokerage_account_number",
        ),
    )

    #
    # Primary Key
    #

    id: Mapped[int] = mapped_column(primary_key=True)

    #
    # Foreign Key
    #

    brokerage_id: Mapped[int] = mapped_column(
        ForeignKey("brokerages.id"),
        nullable=False,
    )

    #
    # Account Information
    #

    account_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    account_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    owner: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    account_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
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

    brokerage: Mapped["Brokerage"] = relationship(
        back_populates="accounts",
    )

    holding_snapshots: Mapped[list["HoldingSnapshot"]] = relationship(
        back_populates="account",
    )

    def __repr__(self) -> str:
        """
        Return a concise representation of the account.
        """
        return (
            f"Account("
            f"id={self.id}, "
            f"number='{self.account_number}', "
            f"name='{self.account_name}')"
        )