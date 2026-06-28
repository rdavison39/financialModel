"""
base.py

Defines the SQLAlchemy Declarative Base class used throughout
the Financial Model application.

Every database model inherits from this Base class.

Author:
    Ron Davison / ChatGPT
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    Example:
        class Company(Base):
            __tablename__ = "companies"
            ...
    """

    pass