"""
Portfolio snapshot database model.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class PortfolioSnapshot(Base):
    """Represents the value of an account or consolidated portfolio."""

    __tablename__ = "portfolio_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)

    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=True,
    )

    snapshot_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    total_value: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
        nullable=False,
    )

    daily_change: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
    )

    daily_change_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6), nullable=True,
    )