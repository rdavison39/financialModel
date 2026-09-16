from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# ============================================================
# Database Configuration
# ============================================================

# Project root directory.
#
# database.py is located in:
#     financialModel/src/database.py
#
# Therefore, parent.parent is:
#     financialModel/
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# SQLite database location.
#
# The database is stored outside the source code in:
#     financialModel/database/financial_model.db
DATABASE_PATH = PROJECT_ROOT / "database" / "financial_model.db"


# SQLAlchemy database URL.
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"


# ============================================================
# Database Engine
# ============================================================

engine = create_engine(
    DATABASE_URL,
    echo=False,
)


# ============================================================
# Database Session
# ============================================================

def get_session() -> Session:
    """Return a new SQLAlchemy database session."""
    return Session(engine)