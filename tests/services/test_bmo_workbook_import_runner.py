"""
Unit tests for bmo_workbook_import_runner.py.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from src.database.unit_of_work import UnitOfWork
from src.services.bmo_workbook_import_runner import (
    import_bmo_workbook,
)


def test_import_bmo_workbook_imports_fixture(
    session: Session,
) -> None:
    """
    The BMO workbook runner imports a real workbook fixture.
    """

    bmo_workbook_path = Path(
        "tests/data/bmo/MyHoldings_22427503.xlsx"
    )

    result = import_bmo_workbook(
        bmo_workbook_path,
        session,
    )

    uow = UnitOfWork(session)

    assert result.success is True
    assert result.import_id is not None
    assert result.accounts_imported == 1
    assert result.positions_imported > 0
    assert result.cash_balances_imported > 0

    assert uow.imports.count() == 1
    assert uow.accounts.count() == 1
    assert uow.holdings.count() == result.positions_imported
    assert (
        uow.cash_balances.count()
        == result.cash_balances_imported
    )
