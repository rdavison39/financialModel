"""
settings.py

Application configuration for the Davison Financial Model.

All project paths and global configuration settings are defined here.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """
    Global application settings.
    """

    #
    # Project folders
    #

    project_root: Path = Path(__file__).resolve().parents[2]

    @property
    def data_folder(self) -> Path:
        """
        Return the application data folder.
        """

        return self.project_root / "data"

    @property
    def database_folder(self) -> Path:
        """
        Return the database folder.
        """

        return self.project_root / "database"

    @property
    def reports_folder(self) -> Path:
        """
        Return the reports folder.
        """

        return self.project_root / "reports"

    @property
    def logs_folder(self) -> Path:
        """
        Return the logs folder.
        """

        return self.project_root / "logs"

    #
    # Database
    #

    @property
    def database_file(self) -> Path:
        """
        Return the SQLite database file.
        """

        return self.database_folder / "family.db"

    #
    # Logging
    #

    @property
    def log_file(self) -> Path:
        """
        Return the application log file.
        """

        return self.logs_folder / "financial_model.log"

    #
    # Brokerage
    #

    brokerage_name: str = "BMO InvestorLine"

    #
    # Market Data
    #

    market_history_days: int = 3650

    #
    # Reporting
    #

    default_report_name: str = "FinancialModel.xlsx"


#
# Global settings object
#

settings = Settings()
