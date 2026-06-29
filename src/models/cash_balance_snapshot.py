"""
cash_balance_snapshot.py

Defines the CashBalanceSnapshot SQLAlchemy model.

A CashBalanceSnapshot represents one cash balance held in one
investment account during one brokerage import.

CashBalanceSnapshots are immutable.

Every brokerage import creates new CashBalanceSnapshot records.
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
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.models.account import Account
    from src.models.import_record import Import


class CashBalanceSnapshot(Base):
    """
    Represents one imported cash balance.

    CashBalanceSnapshots are immutable and represent the cash
    balances reported by a brokerage on the import date.
    """

    __tablename__ = "cash_balance_snapshots"

    __table_args__ = (
        Index(
            "ix_cash_balance_import_account",
            "import_id",
            "account_id",
        ),
        UniqueConstraint(
            "import_id",
            "account_id",
            "currency",
            name="uq_cash_balance_snapshot",
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

    #
    # Cash Information
    #

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    cash_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
    )

    #
    # Relationships
    #

    import_record: Mapped["Import"] = relationship(
        back_populates="cash_balance_snapshots",
    )

    account: Mapped["Account"] = relationship(
        back_populates="cash_balance_snapshots",
    )

    def __repr__(self) -> str:
        """
        Return a concise representation of the cash balance snapshot.
        """

        return (
            f"CashBalanceSnapshot("
            f"id={self.id}, "
            f"account_id={self.account_id}, "
            f"currency='{self.currency}', "
            f"cash_balance={self.cash_balance})"
        )