"""
Account database model.
"""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Account(Base):
    """Represents an investment account at a brokerage."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)

    brokerage_id: Mapped[int] = mapped_column(
        ForeignKey("brokerages.id"),
        nullable=False,
    )

    account_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "brokerage_id",
            "account_number",
            name="uq_account_brokerage_number",
        ),
    )