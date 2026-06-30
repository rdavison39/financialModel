"""
bmo_workbook_import_runner.py

Coordinates a complete BMO InvestorLine workbook import.

Author:
    Ron Davison / ChatGPT
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from src.database.unit_of_work import UnitOfWork
from src.importers.bmo_investorline_importer import (
    BMOInvestorLineImporter,
)
from src.services.import_result import ImportResult
from src.services.import_service import ImportService


def import_bmo_workbook(
    workbook_path: str | Path,
    session: Session,
) -> ImportResult:
    """
    Import one BMO InvestorLine workbook into the database.

    Args:
        workbook_path:
            BMO InvestorLine Excel workbook.

        session:
            SQLAlchemy session used for the import transaction.

    Returns:
        ImportResult summarizing the import.
    """

    path = Path(workbook_path)

    importer = BMOInvestorLineImporter(path)
    account = importer.import_account()

    service = ImportService(UnitOfWork(session))

    return service.import_data(
        [account],
        path,
    )
