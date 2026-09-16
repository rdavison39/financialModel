"""
SQLAlchemy model base for the financial model application.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy database models."""