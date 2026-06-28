"""
account.py

Defines the Account model used by the Financial Model.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Integer
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from src.database.base import Base


class AccountType(Enum):
    """Supported brokerage account types."""

    RRSP = "RRSP"
    TFSA = "TFSA"
    MARGIN = "Margin"
    RESP = "RESP"
    TRUST = "Trust"
    CORPORATE = "Corporate"
    CASH = "Cash"
    OTHER = "Other"


class Account(Base):
    """
    Represents a brokerage account.
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    account_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
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
    )

    institution: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="RBC Direct Investing",
    )

    account_type: Mapped[AccountType] = mapped_column(
        SqlEnum(AccountType),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="CAD",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    #
    # Relationships
    #

    holdings: Mapped[list["Holding"]] = relationship(
        "Holding",
        back_populates="account",
        cascade="all, delete-orphan",
    )

    @property
    def is_registered(self) -> bool:
        """
        Returns True if this is a registered account.
        """

        return self.account_type in (
            AccountType.RRSP,
            AccountType.TFSA,
            AccountType.RESP,
        )

    def __repr__(self) -> str:

        return (
            f"Account("
            f"id={self.id}, "
            f"name='{self.account_name}', "
            f"type='{self.account_type.value}', "
            f"owner='{self.owner}')"
        )