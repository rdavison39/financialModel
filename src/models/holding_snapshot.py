"""
Holding snapshot database model.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class HoldingSnapshot(Base):
    """Represents a security holding at a specific point in time."""

    __tablename__ = "holding_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
    )

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        nullable=False,
    )

    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    average_cost: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    market_value: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
    )

    unrealized_gain: Mapped[Decimal] = mapped_column(
        Numeric(20, 6),
        nullable=False,
    )

    unrealized_gain_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
    )

    daily_change: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
    )

    daily_change_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
    )

    previous_close: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )