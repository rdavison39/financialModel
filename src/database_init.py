"""
Database initialization.
"""

from src.database import engine
from src.models.account import Account
from src.models.base import Base
from src.models.brokerage import Brokerage
from src.models.cash_snapshot import CashSnapshot
from src.models.company import Company
from src.models.holding_snapshot import HoldingSnapshot
from src.models.import_record import ImportRecord
from src.models.portfolio_snapshot import PortfolioSnapshot


def initialize_database() -> None:
    """Create all database tables if they do not already exist."""
    Base.metadata.create_all(engine)