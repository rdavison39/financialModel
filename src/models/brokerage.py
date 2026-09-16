"""
Brokerage database model.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Brokerage(Base):
    """Represents a financial provider such as BMO or Nesbitt Burns."""

    __tablename__ = "brokerages"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)