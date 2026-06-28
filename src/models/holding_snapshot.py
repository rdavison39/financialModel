"""
holding_snapshot.py

Defines the HoldingSnapshot SQLAlchemy model.

A HoldingSnapshot represents one security held in one investment
account during one brokerage import.

HoldingSnapshots are immutable.

Every brokerage import creates new HoldingSnapshot records.
Existing records are never modified.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.models.account import Account
    from src.models.company import Company
    from src.models.import_record import Import


class HoldingSnapshot(Base):
    """
    Represents one holding captured during a brokerage import.

    HoldingSnapshots are immutable and represent factual data imported
    from brokerage exports.
    """

    __tablename__ = "holding_snapshots"

    __table_args__ = (
        Index(
            "ix_holding_snapshots_import_account",
            "import_id",
            "account_id",
        ),
    )

    #
    # Primary Key
    #

    id: Mapped[int] = mapped_column(primary_key=True)

    #
    # Foreign Keys
    #

    import_id: Mapped[int] = mapped_column(
        ForeignKey("imports.id"),
        nullable=False,
        index=True,
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

    #
    # Imported Values
    #

    shares: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    average_cost: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
    )

    imported_price: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    imported_market_value: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
    )

    imported_unrealized_gain: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
    )

    imported_dividend: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    imported_yield: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        nullable=False,
    )

    #
    # Relationships
    #

    import_record: Mapped["Import"] = relationship(
        back_populates="holding_snapshots",
    )

    account: Mapped["Account"] = relationship(
        back_populates="holding_snapshots",
    )

    company: Mapped["Company"] = relationship(
        back_populates="holding_snapshots",
    )

    def __repr__(self) -> str:
        """
        Return a concise representation of the holding snapshot.
        """
        return (
            f"HoldingSnapshot("
            f"id={self.id}, "
            f"account_id={self.account_id}, "
            f"company_id={self.company_id}, "
            f"shares={self.shares})"
        )