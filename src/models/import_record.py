"""
Import record database model.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ImportRecord(Base):
    """Represents one imported brokerage Excel snapshot."""

    __tablename__ = "import_records"

    id: Mapped[int] = mapped_column(primary_key=True)

    brokerage_id: Mapped[int] = mapped_column(
        ForeignKey("brokerages.id"),
        nullable=False,
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"),
        nullable=False,
    )

    # Exact source timestamp from the brokerage report.
    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    # Calendar day used to enforce one authoritative snapshot per
    # brokerage/account/day.
    snapshot_day: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    def __init__(self, **kwargs) -> None:
        """
        Derive snapshot_day from snapshot_date when callers do not supply it.

        This keeps older model-level construction code compatible while the
        database still enforces snapshot_day as NOT NULL.
        """
        if (
            "snapshot_day" not in kwargs
            and "snapshot_date" in kwargs
            and kwargs["snapshot_date"] is not None
        ):
            snapshot_date = kwargs["snapshot_date"]
            if isinstance(snapshot_date, datetime):
                kwargs["snapshot_day"] = snapshot_date.date()
            else:
                raise TypeError(
                    "snapshot_date must be a datetime."
                )

        super().__init__(**kwargs)

    __table_args__ = (
        UniqueConstraint(
            "brokerage_id",
            "account_id",
            "snapshot_day",
            name="uq_import_brokerage_account_snapshot_day",
        ),
    )
