"""
Import record database model.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
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

    snapshot_date: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "brokerage_id",
            "account_id",
            "snapshot_date",
            name="uq_import_brokerage_account_snapshot",
        ),
    )