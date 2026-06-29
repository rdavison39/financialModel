"""
import_record.py

Defines the Import SQLAlchemy model.

An Import represents one brokerage import operation.

Each time brokerage files are imported, a new Import record is created.
All HoldingSnapshots created during that import reference this record.

Imports are immutable and provide the historical audit trail for the
entire application.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from src.database.base import Base

if TYPE_CHECKING:
    from src.models.brokerage import Brokerage
    from src.models.cash_balance_snapshot import CashBalanceSnapshot
    from src.models.holding_snapshot import HoldingSnapshot


class Import(Base):
    """
    Represents one brokerage import operation.
    """

    __tablename__ = "imports"

    #
    # Primary Key
    #

    id: Mapped[int] = mapped_column(primary_key=True)

    #
    # Foreign Keys
    #

    brokerage_id: Mapped[int] = mapped_column(
        ForeignKey("brokerages.id"),
        nullable=False,
    )

    #
    # Import Information
    #

    import_timestamp: Mapped[datetime] = mapped_column(
    DateTime,
    nullable=False,
    default=lambda: datetime.now(UTC),
    index=True,
    )

    source_folder: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    file_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    account_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    holding_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    validation_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    #
    # Relationships
    #

    brokerage: Mapped["Brokerage"] = relationship(
        back_populates="imports",
    )

    holding_snapshots: Mapped[list["HoldingSnapshot"]] = relationship(
        back_populates="import_record",
    )

    cash_balance_snapshots: Mapped[
        list["CashBalanceSnapshot"]
    ] = relationship(
        back_populates="import_record",
    )

    def __repr__(self) -> str:
        """
        Return a concise representation of the import.
        """
        return (
            f"Import("
            f"id={self.id}, "
            f"timestamp='{self.import_timestamp}', "
            f"accounts={self.account_count}, "
            f"holdings={self.holding_count})"
        )